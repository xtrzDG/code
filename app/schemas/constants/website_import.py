from enum import StrEnum


class WebsiteImportStatus(StrEnum):
    """
    Where a website import stands: waiting for a worker, reading pages,
    done (its drafts wait for the owner's review), or failed.
    """

    QUEUED = "queued"
    READING = "reading"
    DONE = "done"
    FAILED = "failed"


class WebsiteImportProblem(StrEnum):
    """
    Why a website import failed (`problem` of the import, with a
    machine-readable `problem_detail` such as "not_public" or
    "http_status:404"):

    - website_link_invalid: not a public http(s) address on port 80/443;
    - website_link_unreachable: the first page could not be fetched
      (unknown host, timeout, no connection, HTTP error, redirects);
    - website_link_unreadable: the first page is not a web page or text,
      or is too large;
    - website_reader_unavailable: no page could be read because the
      reading model failed;
    - website_import_interrupted: the import stopped and was not finished
      (the worker failed repeatedly).
    """

    INVALID = "website_link_invalid"
    UNREACHABLE = "website_link_unreachable"
    UNREADABLE = "website_link_unreadable"
    READER_UNAVAILABLE = "website_reader_unavailable"
    INTERRUPTED = "website_import_interrupted"
