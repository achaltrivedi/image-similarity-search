import cv2
import numpy as np
from PIL import Image

def find_subimage_bounding_box(query_image: Image.Image, full_image: Image.Image) -> list[dict] | None:
    """
    Uses SIFT feature matching to find the location of `query_image` inside `full_image`.
    Returns a list of 4 points {x, y} representing the bounding polygon, or None if no match.
    """
    try:
        # Convert PIL images to OpenCV format (grayscale for feature matching)
        query_cv = cv2.cvtColor(np.array(query_image.convert('RGB')), cv2.COLOR_RGB2GRAY)
        full_cv = cv2.cvtColor(np.array(full_image.convert('RGB')), cv2.COLOR_RGB2GRAY)

        # Scale down large images for faster SIFT matching
        MAX_DIM = 1000
        scale_qs = 1.0
        if max(query_cv.shape) > MAX_DIM:
            scale_qs = MAX_DIM / max(query_cv.shape)
            new_size_q = (int(query_cv.shape[1] * scale_qs), int(query_cv.shape[0] * scale_qs))
            query_cv = cv2.resize(query_cv, new_size_q)
            
        scale_fs = 1.0
        if max(full_cv.shape) > MAX_DIM:
            scale_fs = MAX_DIM / max(full_cv.shape)
            new_size_f = (int(full_cv.shape[1] * scale_fs), int(full_cv.shape[0] * scale_fs))
            full_cv = cv2.resize(full_cv, new_size_f)

        # Initialize SIFT detector
        sift = cv2.SIFT_create()

        # Find keypoints and descriptors
        kp1, des1 = sift.detectAndCompute(query_cv, None)
        kp2, des2 = sift.detectAndCompute(full_cv, None)

        if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
            return None

        # FLANN parameters
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)

        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)

        # Lowe's ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)

        # Need at least 10 good matches to compute homography reliably
        MIN_MATCH_COUNT = 10
        if len(good_matches) > MIN_MATCH_COUNT:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            # Find homography matrix mapping query to full image
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

            # We will generate the box coordinates from M if possible
            box_coords = None
            
            if M is not None:
                h, w = query_cv.shape
                pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
                dst = cv2.perspectiveTransform(pts, M)
                
                # Geometric Validation: Prevent non-linear "bowtie" or impossible distortions
                dst_int = dst.astype(np.int32)
                if cv2.isContourConvex(dst_int):
                    area = cv2.contourArea(dst)
                    fh, fw = full_cv.shape
                    total_area = fh * fw
                    if total_area * 0.001 < area <= total_area:
                        box_coords = dst
                        
            # FALLBACK 1: Distorted Homography -> Use Bounding Rect of Mathematical Inliers
            # Only use if we have a robust dense cluster to avoid drawing boxes from noisy scattered RANSAC points
            if box_coords is None and mask is not None:
                inliers = dst_pts[mask.ravel() == 1]
                if len(inliers) >= 10:
                    ix, iy, iw, ih = cv2.boundingRect(inliers)
                    box_coords = np.float32([
                        [[ix, iy]],
                        [[ix, iy + ih]],
                        [[ix + iw, iy + ih]],
                        [[ix + iw, iy]]
                    ])
                    
            # Format to JSON if SIFT succeeded
            if box_coords is not None:
                fh, fw = full_cv.shape
                box_json = []
                for pt in box_coords:
                    nx = max(0.0, min(1.0, float(pt[0][0]) / fw))
                    ny = max(0.0, min(1.0, float(pt[0][1]) / fh))
                    box_json.append({"x": nx, "y": ny})
                return box_json

        # FALLBACK 2: SIFT failed entirely -> Strict Template Matching
        # Only valid when the query is at a similar scale to the full image region
        # (i.e., NOT a zoomed-in sub-part crop -- those will never pixel-match due to scale difference)
        qh, qw = query_cv.shape
        fh, fw = full_cv.shape
        query_area_ratio = (qh * qw) / (fh * fw)
        
        if (query_area_ratio >= 0.05  # query must be at least 5% of the full image area
                and qh <= fh and qw <= fw):
            res = cv2.matchTemplate(full_cv, query_cv, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            # Confidence threshold must be STRICT (>0.85) to avoid drawing irrelevant boxes on merely "similar" images
            if max_val > 0.85:
                tx, ty = max_loc
                th, tw = query_cv.shape
                
                return [
                    {"x": float(tx) / fw, "y": float(ty) / fh},
                    {"x": float(tx) / fw, "y": float(ty + th) / fh},
                    {"x": float(tx + tw) / fw, "y": float(ty + th) / fh},
                    {"x": float(tx + tw) / fw, "y": float(ty) / fh}
                ]

        return None
    except Exception as e:
        print(f"Localization error: {e}")
        return None
