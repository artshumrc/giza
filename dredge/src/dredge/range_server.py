from __future__ import annotations

import shutil
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import BinaryIO


class RangeRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send_head(self) -> BinaryIO | None:
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            parts = self.path.split("?", 1)[0].split("#", 1)[0]
            if not parts.endswith("/"):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", parts + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            for index in ("index.html", "index.htm"):
                index_path = path / index
                if index_path.is_file():
                    path = index_path
                    break
            else:
                return self.list_directory(str(path))

        content_type = self.guess_type(str(path))
        try:
            file = path.open("rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        stat = path.stat()
        size = stat.st_size
        byte_range = _parse_range_header(self.headers.get("Range"), size)
        if byte_range is None and self.headers.get("Range"):
            file.close()
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        if byte_range is not None:
            start, end = byte_range
            self._dredge_range = byte_range
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header("Content-type", content_type)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
            self.end_headers()
            return file

        self._dredge_range = None
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(size))
        self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
        self.end_headers()
        return file

    def copyfile(self, source: BinaryIO, outputfile: BinaryIO) -> None:
        byte_range = getattr(self, "_dredge_range", None)
        if byte_range is None:
            shutil.copyfileobj(source, outputfile)
            return

        start, end = byte_range
        source.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def serve_range_directory(directory: Path, host: str, port: int) -> None:
    root = directory.resolve()
    handler = partial(RangeRequestHandler, directory=str(root))
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"serving {root} with HTTP Range support at http://{host}:{port}/")
        server.serve_forever()


def _parse_range_header(header: str | None, size: int) -> tuple[int, int] | None:
    if not header or not header.startswith("bytes=") or size < 1:
        return None
    spec = header[len("bytes=") :].strip()
    if "," in spec or "-" not in spec:
        return None

    start_text, end_text = spec.split("-", 1)
    try:
        if start_text == "":
            suffix_length = int(end_text)
            if suffix_length <= 0:
                return None
            start = max(size - suffix_length, 0)
            end = size - 1
        else:
            start = int(start_text)
            end = size - 1 if end_text == "" else int(end_text)
    except ValueError:
        return None

    if start < 0 or end < start or start >= size:
        return None
    return start, min(end, size - 1)
