"""Slurp blog posts and images."""
import argparse
import asyncio
import logging
import os
import os.path
import re
import sys
from datetime import datetime

import aiohttp
from aiofiles import open as async_open
from aiofiles import os as async_os
from aiohttp import ClientSession
from bs4 import BeautifulSoup

DEFAULT_POST_FOLDER = "posts"
DEFAULT_BLOG_URL = "http://ezraandkian.blogspot.com/"
DEFAULT_BLOG_YEAR = int(datetime.now().date().strftime("%Y"))


logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level=logging.DEBUG,
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
logging.getLogger("chardet.charsetprober").disabled = True


async def fetch_resp(url: str, session: ClientSession, **kwargs) -> str:
    """Get generic response."""
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    return resp


async def fetch_html(url: str, session: ClientSession, **kwargs) -> str:
    """Get post html."""
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    html = await resp.text()
    return html


def get_month_links(soup, year, month):
    """Parse html for month links."""
    archive_list = soup.find(attrs={"id": "BlogArchive1_ArchiveList"})
    uls = archive_list.findChildren("ul", recursive=False)

    pattern = re.compile(
        r"^(\w|\:|\/|\.)+" + str(year) + "/" + str(month).zfill(2) + r"/(\w|\-)+"
    )

    for unordered_list in uls:
        for child in unordered_list.findChildren(recursive=False):
            link = child.find("a", attrs={"class", "post-count-link"}, recursive=False)
            link_year = int(link.text.strip())
            if link_year == year:
                month_links = unordered_list.find_all("a")
                elinks = [
                    ml.get("href")
                    for ml in month_links
                    if pattern.match(ml.get("href"))
                ]

                return elinks
    return None


async def get_posts_by_year(blog_url, year, month, session):
    """Find post for given year."""
    try:
        url = blog_url + str(year) + "/" + str(month).zfill(2)
        response = await fetch_html(url=url, session=session)

    except (aiohttp.ClientError, aiohttp.http_exceptions.HttpProcessingError,) as ex:
        LOGGER.error(
            "aiohttp exception for %s [%s]: %s",
            url,
            getattr(ex, "status", None),
            getattr(ex, "message", None),
        )
    else:

        soup = BeautifulSoup(response, "html.parser")
        month_links = get_month_links(soup, year, month)
        return month_links


async def get_post_info(post_link, session):
    """Get blog post text and image names."""
    try:
        response = await fetch_html(url=post_link, session=session)

    except (aiohttp.ClientError, aiohttp.http_exceptions.HttpProcessingError,) as ex:
        LOGGER.error(
            "aiohttp exception for %s [%s]: %s",
            post_link,
            getattr(ex, "status", None),
            getattr(ex, "message", None),
        )
    else:
        clean_post_title = None
        soup = BeautifulSoup(response, "html.parser")

        post_date_str = soup.find(attrs={"class": "date-header"}).text.strip()
        post_date_time = datetime.strptime(post_date_str, "%A, %B %d, %Y")
        post_date = post_date_time.strftime("%Y%m%d")

        post_title_el = soup.find(attrs={"class": "post-title"})
        if post_title_el:
            post_title = post_title_el.text.strip()
            clean_post_title = "".join(e for e in post_title if e.isalnum() or e == " ")
            clean_post_title = clean_post_title.strip()

        post_body = soup.find(attrs={"class": "post-body"})

        if not clean_post_title:
            clean_post_title = "No Post Title"

        post_body_clean = clean_post_title + "\n\n"

        post_body_clean = post_body_clean + "\n\n".join(
            [s.strip() for s in post_body.text.strip().splitlines() if s]
        )

        post_images = post_body.find_all("img")

        post_body_clean = post_body_clean + "\n\n"
        for img in post_images:
            img_name_parts = img.get("src").split("/")
            if "NEF" in img_name_parts:
                post_body_clean = post_body_clean + "!!!WARNING FILE TYPE!!!! "
            post_body_clean = post_body_clean + img_name_parts[-1] + "\n"

        return (
            post_date + "-" + clean_post_title + ".txt",
            post_body_clean,
            post_images,
        )


async def save_post_info(post):
    """Save post text to folder."""
    subdirectory = post[0].split(".")[0]
    file_name, post_text, _ = post
    folder_name = os.path.join(get_post_folder(), subdirectory)

    LOGGER.info("Making folder: %s", folder_name)

    if not await async_os.path.exists(folder_name):
        await async_os.mkdir(folder_name)
    else:
        LOGGER.info("Folder already exists to make folder:  %s", folder_name)

    full_file_name = os.path.join(folder_name, file_name)
    async with async_open(full_file_name, "w", encoding="utf8") as file:
        await file.write(post_text)


async def save_post_images(post_image_link, sub_directory, session):
    """Save post images."""


    img_parts = post_image_link.get("src").split("/")
    # img_parts[-2] = "s2400"  # Why adding s2400? This is breaking images in 202110
    img_url = "/".join(img_parts)

    dest_path = os.path.join(
        get_post_folder(), sub_directory, os.path.basename(img_url)
    )

    try:
        async with session.get(img_url) as response:

            # headers = response.headers
            # if "filename" in headers:
            #     img_name = headers["inline;filename"]
            #     dest_path = os.path.join(
            #         get_post_folder(), sub_directory, img_name
            #     )
            with open(dest_path, "wb") as post_file:
                async for data in response.content.iter_chunked(1024):
                    post_file.write(data)

    except (aiohttp.ClientError, aiohttp.http_exceptions.HttpProcessingError,FileNotFoundError) as ex:
        LOGGER.error(
            "aiohttp exception for %s [%s]: %s",
            img_url,
            getattr(ex, "status", None),
            getattr(ex, "message", None),
        )


async def slurp_blog(blog_url, year, month, session):
    """Slurp posts and images for given month."""
    post_links = await get_posts_by_year(blog_url, year, month, session)

    for post_link in post_links:

        post = await get_post_info(post_link, session)

        _, _, post_images = post

        await save_post_info(post)

        sub_directory = post[0].split(".")[0]
        tasks = []
        for post_image_link in post_images:
            tasks.append(save_post_images(post_image_link, sub_directory, session))
        await asyncio.gather(*tasks)


def get_post_folder():
    """Get post folder."""
    current_dir = os.getcwd()
    folder_name = os.path.join(current_dir, DEFAULT_POST_FOLDER)
    return folder_name


async def create_post_folder():
    """Create post folder."""
    folder_name = get_post_folder()

    LOGGER.info("Making folder: %s", folder_name)

    if not await async_os.path.exists(folder_name):
        await async_os.mkdir(folder_name)
    else:
        LOGGER.info("Folder already exists to make folder:  %s", folder_name)


async def main():
    """Slurp each month."""
    parser = argparse.ArgumentParser(description="Slurp blog.", add_help=True,)
    parser.add_argument(
        "--blog_url", "-u", help="Blog URL.",
    )
    parser.add_argument(
        "--year", "-y", type=int, help="Year to slurp. Default is current year",
    )
    parser.add_argument(
        "--month", "-m", type=int, help="Month to slurp. Default is all months",
    )

    args = parser.parse_args()

    blog_url = args.blog_url or os.environ.get("BLOG_URL")
    blog_year = args.year or os.environ.get("BLOG_YEAR")
    blog_month = args.month

    if not blog_url:
        raise ValueError(
            "The blog url is required."
            "Have you set the BLOG_URL env variable?"
        )

    if not blog_year:
        raise ValueError(
            "The year is required."
            "Have you set the BLOG_YEAR env variable?"
        )


    # check that posts folder exists
    await create_post_folder()

    async with ClientSession() as session:
        tasks = []
        if blog_month:
            tasks.append(slurp_blog(blog_url, blog_year, blog_month, session))
        else:
            for i in range(12):
                tasks.append(slurp_blog(blog_url, blog_year, i + 1, session))
        await asyncio.gather(*tasks)


if __name__ == "__main__":

    # asyncio.run(main())
    asyncio.get_event_loop().run_until_complete(main())
