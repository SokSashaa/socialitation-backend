import os


def delete_image(image_url):
    if os.path.isfile(image_url):
        os.remove(image_url)