import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from os import walk
from os.path import abspath, dirname, join

import cv2
import numpy as np

from core.screen_capture import ScreenCapture

# Initialize ScreenCapture to take screenshots for image analysis
sc = ScreenCapture()

def get_file_count(folder):
    """
    Counts the number of files in a specified directory.

    Args:
        folder (str): The name of the subfolder within 'reference_images' to count files from.

    Returns:
        int: The total number of files found in the directory.
    """
    # Construct the absolute path to the directory
    directory = join(dirname(__file__), "reference_images", folder)
    # Use os.walk to traverse the directory and sum the number of files
    return sum(len(files) for _, _, files in walk(directory))

def make_reference_image_list(size):
    """
    Generates a list of image filenames (e.g., ["1.png", "2.png", ...])
    based on a given size.

    Args:
        size (int): The number of image filenames to generate.

    Returns:
        list[str]: A list of generated image filenames.
    """
    reference_image_list = []
    for index in range(1,size+1):
        image_name: str = f"{index}.png"
        reference_image_list.append(image_name)
    return reference_image_list

def get_first_location(
    locations: list[list[int] | None], flip=False,
) -> list[int] | None:
    """
    Retrieves the first valid (non-None) location from a list of locations.
    Optionally flips the coordinates (x, y) to (y, x).

    Args:
        locations (list[list[int] | None]): A list of potential image locations,
                                            where each location is [x, y] or None.
        flip (bool, optional): If True, flips the coordinates of the found location.
                               Defaults to False.

    Returns:
        list[int] | None: The first found location as [x, y] (or [y, x] if flipped),
                          or None if no valid location is found.
    """
    return next(
        (
            [location[1], location[0]] if flip else location
            for location in locations
            if location is not None
        ),
        None,
    )

def crop_image(image: np.ndarray, region: list) -> np.ndarray:
    """
    Crops a given image based on a specified rectangular region.

    Args:
        image (np.ndarray): The input image (as a NumPy array) to be cropped.
        region (list): A list [left, top, width, height] defining the cropping area.
                       'left' and 'top' are the coordinates of the top-left corner,
                       'width' and 'height' define the dimensions of the region.

    Returns:
        np.ndarray: The cropped image as a NumPy array.
    """
    left, top, width, height = region
    # Crop the image using NumPy array slicing
    cropped_image = image[top : top + height, left : left + width]
    return cropped_image

def check_for_location(locations: list[list[int] | None]):
    """
    Checks if any valid (non-None) location exists in a list of locations.

    Args:
        locations (list[list[int] | None]): A list of potential image locations.

    Returns:
        bool: True if at least one valid location is found, False otherwise.
    """
    return any(location is not None for location in locations)

def find_references(
    image: np.ndarray,
    template_paths: list[str],
    tolerance=0.88,
) -> list[list[int] | None]:
    """
    Finds all occurrences of multiple template images within a larger screenshot.
    Uses multithreading for parallel comparison of templates, improving performance.

    Args:
        image (np.ndarray): The screenshot (as a NumPy array) to search within.
        template_paths (list[str]): A list of absolute paths to the template images to find.
        tolerance (float, optional): The matching threshold (0.0 to 1.0).
                                     Higher values mean a stricter match.
                                     Defaults to 0.88.

    Returns:
        list[list[int] | None]: A list of found coordinates [x, y] for each template.
                                If a template is not found, its entry will be None.
    """
    # Load all template images from their paths
    reference_images = [cv2.imread(path) for path in template_paths]

    # Use a ThreadPoolExecutor to compare images in parallel
    with ThreadPoolExecutor(
        max_workers=len(reference_images), thread_name_prefix="EmulatorThread",
    ) as executor:
        # Submit each image comparison as a separate task
        futures: list[Future[list[int] | None]] = [
            executor.submit(
                compare_images,
                image,
                template,
                tolerance,
            )
            for template in reference_images
        ]
        # Collect and return the results as they complete
        return [future.result() for future in as_completed(futures)]

def compare_images(
    image: np.ndarray,
    template: np.ndarray,
    threshold=0.8,
):
    """
    Compares a template image against a larger image to find its location.
    Uses OpenCV's template matching (TM_CCOEFF_NORMED method).

    Args:
        image (np.ndarray): The larger image (screenshot) to search within.
        template (np.ndarray): The smaller template image to find.
        threshold (float, optional): The matching threshold (0.0 to 1.0).
                                     Defaults to 0.8.

    Returns:
        list[int] | None: The [x, y] coordinates of the top-left corner of the matched area,
                          or None if no match is found above the threshold.
    """
    # Convert images to grayscale for template matching (improves performance and robustness)
    img_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)  # type: ignore
    template_gray = cv2.cvtColor(  # type: ignore
        template,
        cv2.COLOR_RGB2GRAY,  # type: ignore
    )

    # Perform template matching using normalized cross-correlation
    res = cv2.matchTemplate(  # type: ignore
        img_gray,
        template_gray,
        cv2.TM_CCOEFF_NORMED,  # type: ignore
    )

    # Find locations where the match result is above the specified threshold
    loc = np.where(res >= threshold)  # type: ignore

    # Return the location if exactly one match is found, otherwise None
    # This assumes templates are unique and only one instance is expected.
    return None if len(loc[0]) != 1 else [int(loc[0][0]), int(loc[1][0])]

# --- Pixel Comparison Functions ---

def line_is_color(  # pylint: disable=too-many-arguments
     x_1, y_1, x_2, y_2, color, screenshot_np: np.ndarray | None = None,
) -> bool:
    """
    Checks if all pixels along a line segment on the screen match a specified color
    within a given tolerance.

    Args:
        x_1 (int): Starting x-coordinate of the line.
        y_1 (int): Starting y-coordinate of the line.
        x_2 (int): Ending x-coordinate of the line.
        y_2 (int): Ending y-coordinate of the line.
        color (tuple[int, int, int]): The target color as an (R, G, B) tuple.
        screenshot_np (np.ndarray | None): Optional. An existing screenshot as a NumPy array.
                                         If None, a new screenshot will be taken.

    Returns:
        bool: True if all pixels on the line match the color, False otherwise.
    """
    coordinates = get_line_coordinates(x_1, y_1, x_2, y_2)
    if screenshot_np is None:
        screenshot_path, screenshot_np = sc.take_screenshot()
        if screenshot_np is None:
            return False
    iar = np.asarray(screenshot_np)

    for coordinate in coordinates:
        # Get the pixel color at the current coordinate
        pixel = iar[coordinate[1]][coordinate[0]]
        # Convert pixel format if necessary
        pixel = convert_pixel(pixel)

        # If any pixel does not match, return False immediately
        if not pixel_is_equal(color, pixel, tol=35):
            return False
    return True

def check_line_for_color( x_1, y_1, x_2, y_2, color: tuple[int, int, int], screenshot_np: np.ndarray | None = None,
) -> bool:
    """
    Checks if at least one pixel along a line segment on the screen matches a specified color
    within a given tolerance.

    Args:
        x_1 (int): Starting x-coordinate of the line.
        y_1 (int): Starting y-coordinate of the line.
        x_2 (int): Ending x-coordinate of the line.
        y_2 (int): Ending y-coordinate of the line.
        color (tuple[int, int, int]): The target color as an (R, G, B) tuple.
        screenshot_np (np.ndarray | None): Optional. An existing screenshot as a NumPy array.
                                         If None, a new screenshot will be taken.

    Returns:
        bool: True if at least one pixel on the line matches the color, False otherwise.
    """
    coordinates = get_line_coordinates(x_1, y_1, x_2, y_2)
    if screenshot_np is None:
        screenshot_path, screenshot_np = sc.take_screenshot()
        if screenshot_np is None:
            return False
    iar = np.asarray(screenshot_np)

    for coordinate in coordinates:
        # Get the pixel color at the current coordinate
        pixel = iar[coordinate[1]][coordinate[0]]
        # Convert pixel format if necessary
        pixel = convert_pixel(pixel)

        # If a matching pixel is found, return True immediately
        if pixel_is_equal(color, pixel, tol=35):
            return True
    return False

def check_region_for_color( region, color, screenshot_np: np.ndarray | None = None):
    """
    Checks if at least one pixel within a specified rectangular region on the screen
    matches a given color within a tolerance.

    Args:
        region (list): A list [left, top, width, height] defining the area to check.
        color (tuple[int, int, int]): The target color as an (R, G, B) tuple.
        screenshot_np (np.ndarray | None): Optional. An existing screenshot as a NumPy array.
                                         If None, a new screenshot will be taken.

    Returns:
        bool: True if at least one pixel in the region matches the color, False otherwise.
    """
    left, top, width, height = region
    if screenshot_np is None:
        screenshot_path, screenshot_np = sc.take_screenshot()
        if screenshot_np is None:
            return False
    iar = np.asarray(screenshot_np)

    # Iterate through each pixel in the region
    for x_index in range(left, left + width):
        for y_index in range(top, top + height):
            # Get the pixel color
            pixel = iar[y_index][x_index]
            # Convert pixel format
            pixel = convert_pixel(pixel)
            # If a matching pixel is found, return True
            if pixel_is_equal(color, pixel, tol=35):
                return True

    return False

def region_is_color(region, color, screenshot_np: np.ndarray | None = None):
    """
    Checks if all sampled pixels within a specified rectangular region on the screen
    match a given color within a tolerance.
    This function samples pixels by stepping through the region (every 2 pixels).

    Args:
        region (list): A list [left, top, width, height] defining the area to check.
        color (tuple[int, int, int]): The target color as an (R, G, B) tuple.
        screenshot_np (np.ndarray | None): Optional. An existing screenshot as a NumPy array.
                                         If None, a new screenshot will be taken.

    Returns:
        bool: True if all sampled pixels in the region match the color, False otherwise.
    """
    left, top, width, height = region
    if screenshot_np is None:
        screenshot_path, screenshot_np = sc.take_screenshot()
        if screenshot_np is None:
            return False
    iar = np.asarray(screenshot_np)

    # Iterate through sampled pixels in the region
    for x_index in range(left, left + width, 2):
        for y_index in range(top, top + height, 2):
            # Get the pixel color
            pixel = iar[y_index][x_index]
            # Convert pixel format
            pixel = convert_pixel(pixel)
            # If any sampled pixel does not match, return False
            if not pixel_is_equal(color, pixel, tol=35):
                return False

    return True

def convert_pixel(bad_format_pixel):
    """
    Converts a pixel from BGR (OpenCV default) to RGB format.

    Args:
        bad_format_pixel (list/tuple): A pixel in BGR format (e.g., [B, G, R]).

    Returns:
        list[int]: The pixel in RGB format [R, G, B].
    """
    red = bad_format_pixel[2]
    green = bad_format_pixel[1]
    blue = bad_format_pixel[0]
    return [red, green, blue]

def condense_coordinates(coords, distance_threshold=5):
    """
    Condenses a list of coordinates by removing those that are very close to each other.
    This is useful for filtering out redundant detections from image matching.

    Args:
        coords (list): A list of coordinates, where each coordinate is [x, y].
        distance_threshold (int, optional): The maximum distance for two coordinates
                                            to be considered similar and thus condensed.
                                            Defaults to 5.

    Returns:
        list: A list of condensed (unique) coordinates.
    """
    condensed_coords = []

    for coord in coords:
        x, y = coord
        # Check if the current coordinate is too close to any already condensed coordinate
        if not any(
            np.abs(existing_coord[0] - x) < distance_threshold
            and np.abs(existing_coord[1] - y) < distance_threshold
            for existing_coord in condensed_coords
        ):
            condensed_coords.append(coord)

    return condensed_coords

def pixel_is_equal(
    pix1: tuple[int, int, int] | list[int],
    pix2: tuple[int, int, int] | list[int],
    tol: float,
):
    """
    Compares two pixels to check if they are approximately equal within a given tolerance.

    Args:
        pix1 (tuple[int, int, int] | list[int]): The first pixel (R, G, B).
        pix2 (tuple[int, int, int] | list[int]): The second pixel (R, G, B).
        tol (float): The maximum allowed difference for each color channel (tolerance).

    Returns:
        bool: True if the pixels are equal within the tolerance, False otherwise.
    """
    # Calculate the absolute difference for each color channel
    diff_r = abs(int(pix1[0]) - int(pix2[0]))
    diff_g = abs(int(pix1[1]) - int(pix2[1]))
    diff_b = abs(int(pix1[2]) - int(pix2[2]))
    # Check if all differences are within the tolerance
    return (diff_r < tol) and (diff_g < tol) and (diff_b < tol)

def get_line_coordinates(x_1, y_1, x_2, y_2) -> list[tuple[int, int]]:
    """
    Generates a list of (x, y) coordinates representing a line segment
    between two given points using Bresenham's line algorithm.

    Args:
        x_1 (int): Starting x-coordinate.
        y_1 (int): Starting y-coordinate.
        x_2 (int): Ending x-coordinate.
        y_2 (int): Ending y-coordinate.

    Returns:
        list[tuple[int, int]]: A list of (x, y) tuples forming the line.
    """
    coordinates = []
    delta_x = abs(x_2 - x_1)
    delta_y = abs(y_2 - y_1)
    step_x = -1 if x_1 > x_2 else 1
    step_y = -1 if y_1 > y_2 else 1
    error = delta_x - delta_y

    while x_1 != x_2 or y_1 != y_2:
        coordinates.append((x_1, y_1))
        double_error = 2 * error
        if double_error > -delta_y:
            error -= delta_y
            x_1 += step_x
        if double_error < delta_x:
            error += delta_x
            y_1 += step_y

    coordinates.append((x_1, y_1)) # Add the end point
    return coordinates

def pixels_match_colors(pixels,colors,tol=10) -> bool:
    """
    Checks if a list of pixels matches a corresponding list of colors within a tolerance.

    Args:
        pixels (list): A list of pixels (e.g., from a screenshot).
        colors (list): A list of target colors to compare against.
        tol (int, optional): The tolerance for color comparison. Defaults to 10.

    Returns:
        bool: True if all pixels match their corresponding colors, False otherwise.
    """
    for i, p in enumerate(pixels):
        if not pixel_is_equal(p, colors[i], tol=tol):
            return False
    return True