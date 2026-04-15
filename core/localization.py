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

            if M is not None:
                h, w = query_cv.shape
                # Coordinates of the query image corners
                pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
                
                # Transform corners using homography to find location in full image
                dst = cv2.perspectiveTransform(pts, M)
                
                # Normalize coordinates (0.0 to 1.0) so frontend can use percentages
                fh, fw = full_cv.shape
                
                box = []
                for pt in dst:
                    # pt[0][0] is X, pt[0][1] is Y (relative to the scaled full_cv)
                    nx = float(pt[0][0]) / fw
                    ny = float(pt[0][1]) / fh
                    # Clamp coordinates to [0, 1] in case of slight outliers
                    nx = max(0.0, min(1.0, nx))
                    ny = max(0.0, min(1.0, ny))
                    box.append({"x": nx, "y": ny})
                
                return box
        return None
    except Exception as e:
        print(f"Localization error: {e}")
        return None
