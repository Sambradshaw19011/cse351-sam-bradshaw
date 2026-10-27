
"""
Course: CSE 351
Assignment: 06
Author: Sam Bradshaw

Processes face images using multiprocessing queues and worker processes.
"""

import multiprocessing as mp
import os
import cv2

from cse351 import *

# Folders
INPUT_FOLDER = "faces"
STEP1_OUTPUT_FOLDER = "step1_smoothed"
STEP2_OUTPUT_FOLDER = "step2_grayscale"
STEP3_OUTPUT_FOLDER = "step3_edges"

# Parameters for image processing
GAUSSIAN_BLUR_KERNEL_SIZE = (5, 5)
CANNY_THRESHOLD1 = 75
CANNY_THRESHOLD2 = 155

# Allowed image extensions
ALLOWED_EXTENSIONS = (".jpg",)

# Worker configuration
NUM_WORKERS = max(1, min(mp.cpu_count(), 4))
STOP_SIGNAL = None


# ---------------------------------------------------------------------------
def create_folder_if_not_exists(folder_path):
    """Create an output folder if it does not exist."""
    os.makedirs(folder_path, exist_ok=True)


# ---------------------------------------------------------------------------
def task_convert_to_grayscale(image):
    """Convert an image to grayscale."""
    if len(image.shape) == 2:
        return image

    if len(image.shape) == 3 and image.shape[2] == 1:
        return image

    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


# ---------------------------------------------------------------------------
def task_smooth_image(image, kernel_size):
    """Apply Gaussian blur to an image."""
    return cv2.GaussianBlur(image, kernel_size, 0)


# ---------------------------------------------------------------------------
def task_detect_edges(image, threshold1, threshold2):
    """Apply Canny edge detection to a grayscale image."""
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return cv2.Canny(image, threshold1, threshold2)


# ---------------------------------------------------------------------------
def smoothing_worker(input_queue, output_folder):
    """Read filenames from the first queue, smooth images, and save them."""
    while True:
        filename = input_queue.get()

        if filename == STOP_SIGNAL:
            break

        input_path = os.path.join(INPUT_FOLDER, filename)
        output_path = os.path.join(output_folder, filename)

        try:
            image = cv2.imread(input_path)

            if image is None:
                print(f"Warning: Could not read {input_path}")
                continue

            result = task_smooth_image(
                image, GAUSSIAN_BLUR_KERNEL_SIZE
            )

            if not cv2.imwrite(output_path, result):
                print(f"Warning: Could not save {output_path}")

        except Exception as error:
            print(f"Error smoothing {filename}: {error}")


# ---------------------------------------------------------------------------
def grayscale_worker(input_queue, output_folder):
    """Read smoothed images, convert them to grayscale, and save them."""
    while True:
        filename = input_queue.get()

        if filename == STOP_SIGNAL:
            break

        input_path = os.path.join(STEP1_OUTPUT_FOLDER, filename)
        output_path = os.path.join(output_folder, filename)

        try:
            image = cv2.imread(input_path)

            if image is None:
                print(f"Warning: Could not read {input_path}")
                continue

            result = task_convert_to_grayscale(image)

            if not cv2.imwrite(output_path, result):
                print(f"Warning: Could not save {output_path}")

        except Exception as error:
            print(f"Error converting {filename} to grayscale: {error}")


# ---------------------------------------------------------------------------
def edge_detection_worker(input_queue, output_folder):
    """Read grayscale images, detect edges, and save the final images."""
    while True:
        filename = input_queue.get()

        if filename == STOP_SIGNAL:
            break

        input_path = os.path.join(STEP2_OUTPUT_FOLDER, filename)
        output_path = os.path.join(output_folder, filename)

        try:
            image = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)

            if image is None:
                print(f"Warning: Could not read {input_path}")
                continue

            result = task_detect_edges(
                image, CANNY_THRESHOLD1, CANNY_THRESHOLD2
            )

            if not cv2.imwrite(output_path, result):
                print(f"Warning: Could not save {output_path}")

        except Exception as error:
            print(f"Error detecting edges for {filename}: {error}")


# ---------------------------------------------------------------------------
def run_processing_stage(input_queue, filenames, worker_function,
                         output_folder):
    """
    Run one processing stage with multiple worker processes.

    The main process adds filenames to the queue and sends one stop
    signal to each worker after all filenames have been added.
    """
    create_folder_if_not_exists(output_folder)

    processes = []

    for _ in range(NUM_WORKERS):
        process = mp.Process(
            target=worker_function,
            args=(input_queue, output_folder)
        )
        processes.append(process)
        process.start()

    for filename in filenames:
        input_queue.put(filename)

    for _ in range(NUM_WORKERS):
        input_queue.put(STOP_SIGNAL)

    for process in processes:
        process.join()

    input_queue.close()
    input_queue.join_thread()


# ---------------------------------------------------------------------------
def run_image_processing_pipeline():
    """Run the three image-processing stages using multiprocessing."""
    print("Starting image processing pipeline...")

    # Get the original image filenames.
    filenames = sorted(
        filename
        for filename in os.listdir(INPUT_FOLDER)
        if os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS
    )

    if not filenames:
        print(f"No images found in '{INPUT_FOLDER}'.")
        return

    print(f"Found {len(filenames)} images to process.")
    print(f"Using {NUM_WORKERS} worker processes per stage.")

    # Queue 1: Original images -> smoothing workers
    queue1 = mp.Queue()

    run_processing_stage(
        queue1,
        filenames,
        smoothing_worker,
        STEP1_OUTPUT_FOLDER
    )

    print(f"Finished smoothing {len(filenames)} image files.")

    # Queue 2: Smoothed images -> grayscale workers
    queue2 = mp.Queue()

    run_processing_stage(
        queue2,
        filenames,
        grayscale_worker,
        STEP2_OUTPUT_FOLDER
    )

    print(f"Finished grayscale conversion for {len(filenames)} image files.")

    # Queue 3: Grayscale images -> edge-detection workers
    queue3 = mp.Queue()

    run_processing_stage(
        queue3,
        filenames,
        edge_detection_worker,
        STEP3_OUTPUT_FOLDER
    )

    print(f"Finished edge detection for {len(filenames)} image files.")

    print("\nImage processing pipeline finished!")
    print(f"Original images are in: '{INPUT_FOLDER}'")
    print(f"Smoothed images are in: '{STEP1_OUTPUT_FOLDER}'")
    print(f"Grayscale images are in: '{STEP2_OUTPUT_FOLDER}'")
    print(f"Edge images are in: '{STEP3_OUTPUT_FOLDER}'")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mp.freeze_support()

    log = Log(show_terminal=True)
    log.start_timer("Processing Images")

    if not os.path.isdir(INPUT_FOLDER):
        print(f"Error: The input folder '{INPUT_FOLDER}' was not found.")
        print("Create it and place your face images inside it.")
        print("Link to faces.zip:")
        print(
            "https://drive.google.com/file/d/"
            "1eebhLE51axpLZoU6s_Shtw1QNcXqtyHM/view?usp=sharing"
        )
    else:
        run_image_processing_pipeline()

    log.write()
    log.stop_timer("Total Time To complete")
