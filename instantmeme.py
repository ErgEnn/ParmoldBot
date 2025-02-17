import discord
import random
import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.python.solutions.drawing_utils import _normalized_to_pixel_coordinates
import io
import logging

OVERLAYS_FOLDER = 'data/faces'


async def try_handle_instant_meme(message):
    if message.content.startswith('$ignore'):
        return;
    if message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
                logging.debug('try_handle_instant_meme',
                              extra={'message_content': message.content, 'message_id': message.id})
                async with message.channel.typing():
                    img = await get_img_from_attachment(attachment)
                    faces = get_faces(img)

                    if not faces.multi_face_landmarks:
                        logging.info('Message {message_id} didnt contain any faces', message_id=message.id)
                        return None

                    if message.content.startswith('$mask'):
                        draw_masks_on_faces(img, faces)
                    elif message.content.startswith('$eyes'):
                        draw_specific_points_on_faces(img, faces)
                    elif message.content.startswith('$explainmin'):
                        draw_letters_on_faces(img, faces, '')
                    elif message.content.startswith('$explainfull'):
                        draw_letters_on_faces(img, faces)
                    else:
                        draw_overlays_on_faces(img, faces)

                    await send_img_to_channel(img, message.channel)


def draw_overlays_on_faces(img, faces):
    points_on_faces = get_specific_points_on_faces(img, faces)

    for face in points_on_faces:
        overlay_filename = random.choice(os.listdir(OVERLAYS_FOLDER))
        overlay_path = os.path.join(OVERLAYS_FOLDER, overlay_filename)

        overlay = get_img_from_path(overlay_path)
        overlay = transform_overlay(img, overlay)
        best_overlay = choose_best_overlay_simple(overlay, face)
        overlay_faces = get_faces(best_overlay, no_of_faces=1)
        points_on_overlay_faces = get_specific_points_on_faces(best_overlay, overlay_faces)

        p1_src = np.array(points_on_overlay_faces[0][0])
        p2_src = np.array(points_on_overlay_faces[0][1])

        p1_dst = np.array(face[0])
        p2_dst = np.array(face[1])

        A = np.array([
            [p1_src[0], -p1_src[1], 1, 0],
            [p1_src[1], p1_src[0], 0, 1],
            [p2_src[0], -p2_src[1], 1, 0],
            [p2_src[1], p2_src[0], 0, 1]
        ])

        b = np.array([p1_dst[0], p1_dst[1], p2_dst[0], p2_dst[1]])

        params, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        a, b_param, tx, ty = params

        M = np.array([
            [a, -b_param, tx],
            [b_param, a, ty]
        ])

        rows, cols = img.shape[:2]
        transformed_overlay = cv2.warpAffine(best_overlay, M, (cols, rows))

        y1, y2 = 0, 0 + transformed_overlay.shape[0]
        x1, x2 = 0, 0 + transformed_overlay.shape[1]

        alpha_s = transformed_overlay[:, :, 3] / 255.0
        alpha_l = 1.0 - alpha_s

        for c in range(0, 3):
            img[y1:y2, x1:x2, c] = (alpha_s * transformed_overlay[:, :, c] +
                                    alpha_l * img[y1:y2, x1:x2, c])

    return img


def get_img_from_path(path):
    overlay_img = cv2.imread(path, -1)
    return overlay_img


def choose_best_overlay_simple(overlay, src_eye_points):
    # Get overlay facial points with validation
    overlay_faces = get_faces(overlay, no_of_faces=1)
    overlay_points = get_specific_points_on_faces(overlay, overlay_faces)

    # Convert to numpy arrays
    src_left = np.array(src_eye_points[0])
    src_right = np.array(src_eye_points[1])
    ovr_left = np.array(overlay_points[0][0])
    ovr_right = np.array(overlay_points[0][1])

    # Flip source eye points horizontally to match the person's perspective
    src_left = np.array([overlay.shape[1] - src_left[0], src_left[1]])  # Mirror left eye
    src_right = np.array([overlay.shape[1] - src_right[0], src_right[1]])  # Mirror right eye

    # Calculate eye vectors
    src_vector = src_right - src_left
    ovr_vector = ovr_right - ovr_left

    # Calculate angle difference using vector dot product
    cos_theta = np.dot(src_vector, ovr_vector) / (np.linalg.norm(src_vector) * np.linalg.norm(ovr_vector))
    angle = np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))

    # Calculate horizontal direction similarity
    src_dx = src_vector[0]
    ovr_dx = ovr_vector[0]
    direction_match = np.sign(src_dx) == np.sign(ovr_dx)

    # Log the computed values
    logging.info(f"Angle difference: {angle} degrees")
    logging.info(f"Source vector: {src_vector}")
    logging.info(f"Overlay vector: {ovr_vector}")
    logging.info(f"Source left eye: {src_left}, Source right eye: {src_right}")
    logging.info(f"Overlay left eye: {ovr_left}, Overlay right eye: {ovr_right}")
    logging.info(f"Direction match: {direction_match}")

    # Combine conditions for reliable flipping
    should_flip = False

    # Condition 1: Significant angle difference or vertical mismatch
    if abs(angle) > 30:  # If angle difference is greater than 30, flip the overlay
        logging.info("Should flip: True (due to angle difference > 30 degrees)")
        should_flip = True
    elif abs(angle) < 15:  # If the angle difference is small
        # Only flip if there is a significant vertical mismatch
        if abs(src_vector[1]) > abs(ovr_vector[1]) * 0.5:
            logging.info("Should flip: True (due to vertical mismatch in small angle case)")
            should_flip = True

    # Condition 2: If the direction is opposite
    if not direction_match and abs(angle) > 45:
        logging.info("Should flip: True (due to direction mismatch and large angle)")
        should_flip = True

    if not should_flip:
        logging.info("Should flip: False")

    # Flip overlay if necessary
    return cv2.flip(overlay, 1) if should_flip else overlay


async def get_img_from_attachment(attachment):
    img_bytes = await attachment.read()
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)
    return img


def get_faces(img, no_of_faces=10):
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=no_of_faces,
        refine_landmarks=True,
        min_detection_confidence=0.5)
    faces = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return faces


def draw_masks_on_faces(img, faces):
    image_rows, image_cols, _ = img.shape
    for face in faces.multi_face_landmarks:
        for mask_point in face.landmark:
            cord = _normalized_to_pixel_coordinates(mask_point.x, mask_point.y, image_cols, image_rows)
            cv2.putText(img, '.', cord, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 2)


def draw_specific_points_on_faces(img, faces, points=[33, 263]):
    image_rows, image_cols, _ = img.shape
    for face in faces.multi_face_landmarks:
        all_points = face.landmark
        for mask_point in points:
            cord = _normalized_to_pixel_coordinates(all_points[mask_point].x, all_points[mask_point].y, image_cols,
                                                    image_rows)
            cv2.putText(img, '.', cord, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 2)


def draw_letters_on_faces(img, faces, alt='.'):
    image_rows, image_cols, _ = img.shape
    letters = {
        33: 'l',
        159: 't',
        133: 'r',
        145: 'b',
        362: 'L',
        386: 'T',
        263: 'R',
        374: 'B',
        61: 'm',  # may be wrong
        409: 'M',  # wrong but close
    }
    for face in faces.multi_face_landmarks:
        all_points = face.landmark
        for mask_point in range(len(all_points)):
            cord = _normalized_to_pixel_coordinates(all_points[mask_point].x, all_points[mask_point].y, image_cols,
                                                    image_rows)
            cv2.putText(img, alt if mask_point not in letters else letters[mask_point], cord, cv2.FONT_HERSHEY_SIMPLEX,
                        0.3, (0, 0, 255), 2)


def get_specific_points_on_faces(img, faces, points=[33, 263]):
    points_on_faces = []
    image_rows, image_cols, _ = img.shape
    for face in faces.multi_face_landmarks:
        all_points = face.landmark
        points_on_face = []
        for mask_point in points:
            cord = _normalized_to_pixel_coordinates(all_points[mask_point].x, all_points[mask_point].y, image_cols,
                                                    image_rows)
            points_on_face.append(cord)
        points_on_faces.append(points_on_face)
    return points_on_faces


def draw_points_on_faces(img, points_on_faces):
    for face in points_on_faces:
        for point in face:
            cv2.putText(img, '.', point, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 2)


async def send_img_to_channel(img, channel):
    _, buffer = cv2.imencode('.png', img)
    output_bytes = buffer.tobytes()
    await channel.send(file=discord.File(fp=io.BytesIO(output_bytes), filename='output.png'))


def calculate_average_brightness(image):
    return np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))


def calculate_average_contrast(image):
    return np.std(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))


def transform_overlay(image, overlay_image):
    # Calculate average brightness and contrast for both images
    source_brightness = calculate_average_brightness(image)
    source_contrast = calculate_average_contrast(image)
    overlay_brightness = calculate_average_brightness(overlay_image)
    overlay_contrast = calculate_average_contrast(overlay_image)

    # Adjust overlay brightness and contrast based on source image
    contrast_factor = source_contrast / overlay_contrast if overlay_contrast != 0 else 1
    brightness_adjustment = source_brightness - overlay_brightness * contrast_factor

    # Apply brightness and contrast adjustment to overlay image
    if overlay_image.shape[2] == 4:
        # Split channels and process only RGB channels
        b, g, r, alpha = cv2.split(overlay_image)
        overlay_rgb = cv2.merge((b, g, r))
        transformed_rgb = cv2.convertScaleAbs(overlay_rgb, alpha=contrast_factor, beta=brightness_adjustment)
        # Re-attach alpha channel
        transformed_overlay = cv2.merge((transformed_rgb, alpha))
    else:
        # Process the overlay without an alpha channel
        transformed_overlay = cv2.convertScaleAbs(overlay_image, alpha=contrast_factor, beta=brightness_adjustment)

    return transformed_overlay
