import os


def delete_image(image_url):
    if (not image_url is None
            and os.path.isfile(image_url)):
        os.remove(image_url)
