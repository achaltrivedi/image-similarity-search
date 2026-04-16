import cv2
import numpy as np
from PIL import Image

def find_subimage_bounding_box(query_image: Image.Image, full_image: Image.Image) -> list[dict] | None:
    """
    Uses multi-scale SIFT feature matching and Template Matching to find the location 
    of `query_image` inside `full_image`.
    Returns a list of 4 points {x, y} representing the bounding polygon, or None if no match.
    """
    try:
        # Convert PIL images to OpenCV format (grayscale for feature matching)
        query_gray = cv2.cvtColor(np.array(query_image.convert('RGB')), cv2.COLOR_RGB2GRAY)
        full_gray = cv2.cvtColor(np.array(full_image.convert('RGB')), cv2.COLOR_RGB2GRAY)

        # Scale down full image for faster matching
        MAX_DIM = 1000
        scale_fs = 1.0
        if max(full_gray.shape) > MAX_DIM:
            scale_fs = MAX_DIM / max(full_gray.shape)
            new_size_f = (int(full_gray.shape[1] * scale_fs), int(full_gray.shape[0] * scale_fs))
            full_cv = cv2.resize(full_gray, new_size_f)
        else:
            full_cv = full_gray

        # Initialize SIFT
        sift = cv2.SIFT_create()
        kp2, des2 = sift.detectAndCompute(full_cv, None)

        if des2 is None or len(kp2) < 4:
            return None

        # FLANN setup
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        best_box_coords = None
        max_inliers = 0
        
        # 1. Multi-Scale SIFT Feature Matching
        scales = [1.0, 0.75, 0.5, 0.25, 1.25, 1.5]
        
        for scale in scales:
            # Constrain max query size
            scale_qs = scale
            if max(query_gray.shape) * scale_qs > MAX_DIM:
                scale_qs = MAX_DIM / max(query_gray.shape)
                
            new_size_q = (int(query_gray.shape[1] * scale_qs), int(query_gray.shape[0] * scale_qs))
            if new_size_q[0] < 10 or new_size_q[1] < 10:
                continue
                
            query_cv = cv2.resize(query_gray, new_size_q)
            kp1, des1 = sift.detectAndCompute(query_cv, None)

            if des1 is None or len(kp1) < 4:
                continue

            matches = flann.knnMatch(des1, des2, k=2)

            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.7 * n.distance:
                        good_matches.append(m)

            MIN_MATCH_COUNT = 5
            if len(good_matches) > MIN_MATCH_COUNT and len(good_matches) > max_inliers:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

                # Optimization #3: High-robustness MAGSAC++ over standard RANSAC
                M, mask = cv2.findHomography(src_pts, dst_pts, cv2.USAC_MAGSAC, 5.0)

                box_coords_candidate = None
                if M is not None:
                    h, w = query_cv.shape
                    pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
                    try:
                        dst = cv2.perspectiveTransform(pts, M)
                        dst_int = dst.astype(np.int32)
                        area = cv2.contourArea(dst)
                        fh, fw = full_cv.shape
                        total_area = fh * fw

                        if area > total_area * 0.00001:
                            if cv2.isContourConvex(dst_int):
                                box_coords_candidate = dst
                            else:
                                ix, iy, iw, ih = cv2.boundingRect(dst_int)
                                box_coords_candidate = np.float32([
                                    [[ix, iy]], [[ix, iy + ih]],
                                    [[ix + iw, iy + ih]], [[ix + iw, iy]]
                                ])
                    except Exception:
                        pass
                
                # Fallback to spanning box
                if box_coords_candidate is None and mask is not None:
                    inliers = dst_pts[mask.ravel() == 1]
                    if len(inliers) >= 4:
                        ix, iy, iw, ih = cv2.boundingRect(inliers)
                        box_coords_candidate = np.float32([
                            [[ix, iy]], [[ix, iy + ih]],
                            [[ix + iw, iy + ih]], [[ix + iw, iy]]
                        ])
                
                if box_coords_candidate is not None:
                    best_box_coords = box_coords_candidate
                    max_inliers = len(good_matches)

        if best_box_coords is not None:
            fh, fw = full_cv.shape
            box_json = []
            for pt in best_box_coords:
                nx = max(0.0, min(1.0, float(pt[0][0]) / fw))
                ny = max(0.0, min(1.0, float(pt[0][1]) / fh))
                box_json.append({"x": nx, "y": ny})
            return box_json

        # 2. Multi-Scale Template Matching Fallback
        # Run if SIFT yields zero valid polygons across all scales
        best_tm_val = -1.0
        best_tm_coords = None
        
        for scale in [1.0, 0.75, 0.5, 0.25]:
            scale_qs = scale
            if max(query_gray.shape) * scale_qs > MAX_DIM:
                scale_qs = MAX_DIM / max(query_gray.shape)
            
            new_size_q = (int(query_gray.shape[1] * scale_qs), int(query_gray.shape[0] * scale_qs))
            if new_size_q[0] < 10 or new_size_q[1] < 10:
                continue
                
            query_cv = cv2.resize(query_gray, new_size_q)
            
            qh, qw = query_cv.shape
            fh, fw = full_cv.shape
            query_area_ratio = (qh * qw) / (fh * fw)

            if query_area_ratio >= 0.001 and qh <= fh and qw <= fw:
                res = cv2.matchTemplate(full_cv, query_cv, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val > 0.85 and max_val > best_tm_val:
                    best_tm_val = max_val
                    tx, ty = max_loc
                    best_tm_coords = [
                        {"x": float(tx) / fw, "y": float(ty) / fh},
                        {"x": float(tx) / fw, "y": float(ty + qh) / fh},
                        {"x": float(tx + qw) / fw, "y": float(ty + qh) / fh},
                        {"x": float(tx + qw) / fw, "y": float(ty) / fh}
                    ]

        if best_tm_coords is not None:
            return best_tm_coords

        return None
    except Exception as e:
        print(f"Localization error: {e}")
        return None
