#!/usr/bin/env python3
"""Slurp all Images and text from the blog into a folder."""
import os
import os.path
import re
import logging
import argparse
import asyncio
from datetime import datetime
from urllib.request import urlopen, urlretrieve
from bs4 import BeautifulSoup


_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
_LOGGER.addHandler(ch)

def get_posts_by_year(blog_url, year, month):
    """Get url for each post by month and year return as list.

    Defaults to returning empty list if no posts are found.
    """
    url = blog_url + str(year) + "/" + str(month).zfill(2)
    response = urlopen(url)
    soup = BeautifulSoup(response, "html.parser")

    archive_list = soup.find(attrs={"id": "BlogArchive1_ArchiveList"})

    uls = archive_list.findChildren("ul", recursive=False)

    pattern = re.compile(
        r"^(\w|\:|\/|\.)+" + str(year) + "/" + str(month).zfill(2) + r"/(\w|\-)+"
    )

    for ul in uls:

        children = ul.findChildren(recursive=False)
        for child in children:
            a = child.find("a", attrs={"class", "post-count-link"}, recursive=False)

            link_year = int(a.text.strip())
            if link_year == year:
                # ml = child.find(
                #     'a',
                #     attrs={'class', 'post-count-link'},
                #     recursive=False
                # )

                month_links = ul.find_all("a")
                elinks = [
                    ml.get("href")
                    for ml in month_links
                    if pattern.match(ml.get("href"))
                ]

    return elinks


def get_post_info(url):
    """Get post text and list of images and return as tuple.

    Defaults to returning empty tuple if post is not found.
    """
    try:

        response = urlopen(url)
        soup = BeautifulSoup(response, "html.parser")

        post_date_str = soup.find(attrs={"class": "date-header"}).text.strip()
        post_date_time = datetime.strptime(post_date_str, "%A, %B %d, %Y")
        post_date = post_date_time.strftime("%Y%m%d")

        post_title = soup.find(attrs={"class": "post-title"}).text.strip()
        clean_post_title = "".join(e for e in post_title if e.isalnum() or e == " ")

        post_body = soup.find(attrs={"class": "post-body"})

        # lines = postBody.text.strip().splitlines()

        post_body_clean = "\n\n".join(
            [s.strip() for s in post_body.text.strip().splitlines() if s]
        )

        post_images = post_body.find_all("img")

        post_body_clean = post_body_clean + "\n\n"
        for img in post_images:
            img_name_parts = img.get("src").split("/")
            post_body_clean = post_body_clean + img_name_parts[-1] + "\n"

        return (post_date + "-" + clean_post_title + ".txt", post_body_clean, post_images)

    except ConnectionResetError:
        _LOGGER.error("Connection closed .. .try again.", exc_info=True)
        return True, "Connection Closed for " + url


def save_post_info(post):
    """Save post data to a file."""
    subdirectory = post[0].split(".")[0]
    file_name, post_text, _ = post

    folder_name = os.path.join("Posts", subdirectory)

    try:
        _LOGGER.info("Making folder: %s", folder_name)
        os.mkdir(folder_name)
    except Exception:
        _LOGGER.error("Failed to make folder %s", folder_name, exc_info=True)

    try:
        full_file_name = os.path.join(folder_name, file_name)
        with open(full_file_name, "w", encoding="utf8") as file:
            file.write(post_text)
    except Exception:
        _LOGGER.error("Failed to save file %s", full_file_name, exc_info=True)


def save_post_images(url):
    """Download post images and save to folder."""
    try:
        response = urlopen(url)

        soup = BeautifulSoup(response, "html.parser")

        post_date_str = soup.find(attrs={"class": "date-header"}).text.strip()
        post_date_time = datetime.strptime(post_date_str, "%A, %B %d, %Y")
        post_date = post_date_time.strftime("%Y%m%d")

        post_title = soup.find(attrs={"class": "post-title"}).text.strip()
        clean_post_title = "".join(e for e in post_title if e.isalnum() or e == " ")
        sub_directory = post_date + "-" + clean_post_title

        post_body = soup.find(attrs={"class": "post-body"})
        post_images = post_body.find_all("img")

        try:
            os.mkdir(os.path.join("Posts", sub_directory))
        except Exception:
            pass

        for img in post_images:
            img_parts = img.get("src").split("/")
            img_parts[-2] = "s2400"

            img_url = "/".join(img_parts)

            try:
                urlretrieve(
                    img_url,
                    os.path.join("Posts", sub_directory, os.path.basename(img_url)),
                )
            except Exception:
                _LOGGER.error(
                    "Failed to download for %s", sub_directory + " " + img_url,
                    exc_info=True,
                )

    except ConnectionResetError:

        _LOGGER.error("Connection closed .. .try again.", exc_info=True)


def slurp_blog(blog_url, year, month):
    """Fetch text and images for a given blog year and month.

    Creates a post folder with a subfolder for each post.
    """
    post_links = get_posts_by_year(blog_url, year, month)

    folder_name = os.path.join("Posts")
    try:
        _LOGGER.info("Making folder: %s", folder_name)
        if(not os.path.isdir(folder_name)):        
            os.mkdir(folder_name)
    except Exception:
        _LOGGER.error("Failed to make folder %s", folder_name, exc_info=True)

    for post_link in post_links:
        # Create a task here
        post = get_post_info(post_link)

        # Wait for post to return
        # Create a task here
        save_post_info(post)
        # Create a task here
        save_post_images(post_link)


def main(blog_url, blog_year):
    """Run the script."""
    for i in range(1):
        # Create a task here
        slurp_blog(blog_url, blog_year, i + 1)


if __name__ == "__main__":
    _LOGGER.info("Starting script")
    parser = argparse.ArgumentParser(
        description="Slurp posts and images from blogger.", add_help=True,
    )
    parser.add_argument("--blog_url", "-b", help="Blog Url")
    parser.add_argument("--year", "-y", type=int,  help="Year to slurp")
    args = parser.parse_args()

    # blog_url = args.blog_url or "http://example.blogspot.com/"
    # blog_year = args.year or 2018

    main(blog_url, blog_year)
