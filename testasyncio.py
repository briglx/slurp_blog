import asyncio
import logging
import re
import sys
import os
import os.path
import re
from typing import IO
import urllib.error
import urllib.parse
from datetime import datetime

import aiofiles
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level=logging.DEBUG,
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)
logging.getLogger("chardet.charsetprober").disabled = True


async def fetch_resp(url: str, session: ClientSession, **kwargs) -> str:
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    return resp

async def fetch_html(url: str, session: ClientSession, **kwargs) -> str:
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    html = await resp.text()
    return html

async def get_posts_by_year(blog_url, year, month, session):

    try:
        url = blog_url + str(year) + "/" + str(month).zfill(2)

        response = await fetch_html(url=url, session=session)

    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as e:
        logger.error(
            "aiohttp exception for %s [%s]: %s",
            url,
            getattr(e, "status", None),
            getattr(e, "message", None),
        )
    except Exception as e:
        logger.exception(
            "Non-aiohttp exception occured:  %s", getattr(e, "__dict__", {})
        )
    else:

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
                    month_links = ul.find_all("a")
                    elinks = [
                        ml.get("href")
                        for ml in month_links
                        if pattern.match(ml.get("href"))
                    ]

        return elinks


async def get_post_info(post_link, session):

    try:
        response = await fetch_html(url=post_link, session=session)

    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as e:
        logger.error(
            "aiohttp exception for %s [%s]: %s",
            post_link,
            getattr(e, "status", None),
            getattr(e, "message", None),
        )
    except Exception as e:
        logger.exception(
            "Non-aiohttp exception occured:  %s", getattr(e, "__dict__", {})
        )
    else:

        soup = BeautifulSoup(response, "html.parser")

        post_date_str = soup.find(attrs={"class": "date-header"}).text.strip()
        post_date_time = datetime.strptime(post_date_str, "%A, %B %d, %Y")
        post_date = post_date_time.strftime("%Y%m%d")

        post_title = soup.find(attrs={"class": "post-title"}).text.strip()
        clean_post_title = "".join(e for e in post_title if e.isalnum() or e == " ")
        clean_post_title = clean_post_title.strip()

        post_body = soup.find(attrs={"class": "post-body"})

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

        return (post_date + "-" + clean_post_title + ".txt", post_body_clean, post_images)


async def save_post_info(post):

    subdirectory = post[0].split(".")[0]
    file_name, post_text, _ = post
    folder_name = os.path.join("Posts", subdirectory)

    logger.info("Making folder: %s", folder_name)

    try:
        os.mkdir(folder_name)
    except Exception:
        logger.exception(
            "Failed to make folder:  %s", folder_name
        )
    else:

        full_file_name = os.path.join(folder_name, file_name)
        async with aiofiles.open(full_file_name, "w", encoding="utf8") as file:
            await file.write(post_text)

async def save_post_images(post_image_link, sub_directory, session):

    img_parts = post_image_link.get("src").split("/")
    img_parts[-2] = "s2400"
    img_url = "/".join(img_parts)

    dest_path = os.path.join("Posts", sub_directory, os.path.basename(img_url))

    try:
        async with session.get(img_url) as response:
            with open(dest_path, 'wb') as fd:
                async for data in response.content.iter_chunked(1024):
                    fd.write(data)

    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as e:
        logger.error(
            "aiohttp exception for %s [%s]: %s",
            img_url,
            getattr(e, "status", None),
            getattr(e, "message", None),
        )
    except Exception as e:
        logger.exception(
            "Non-aiohttp exception occured:  %s", getattr(e, "__dict__", {})
        )
    


async def slurp_blog(blog_url, year, month, session):

    post_links = await get_posts_by_year(blog_url, year, month, session)
    
    for post_link in post_links:
       
        post = await get_post_info(post_link, session)

        _, _, post_images = post

        await save_post_info(post)

        sub_directory = post[0].split(".")[0]
        tasks = []
        for post_image_link in post_images:
            tasks.append(
                save_post_images(post_image_link,sub_directory, session )
            )
        await asyncio.gather(*tasks)

         

async def main(blog_url, blog_year):
    async with ClientSession() as session:
        tasks = []
        for i in range(12):
            tasks.append(
                slurp_blog(blog_url, blog_year, i + 1, session)
            )
        await asyncio.gather(*tasks)
    

if __name__ == "__main__":
    blog_url = "http://ezraandkian.blogspot.com/"
    blog_year = 2020
    asyncio.run(main(blog_url, blog_year))