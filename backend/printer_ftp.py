import aioftp
import ssl
from typing import Literal, ClassVar
from pydantic import BaseModel
from pathlib import PurePosixPath

from contextlib import asynccontextmanager
from typing import AsyncIterator


class PrinterFileSystemEntry(BaseModel):
    entry_type: Literal["file", "dir"]
    path: PurePosixPath
    size: str
    modify: str

    supported_files: ClassVar[list[str]] = [".3mf"]

    @property
    def is_dir(self) -> bool:
        return self.entry_type == "dir"

    @property
    def is_file(self) -> bool:
        return self.entry_type == "file"

    @property
    def is_printable(self) -> bool:
        suffix = self.path.suffix.lower()
        return suffix in self.supported_files


@asynccontextmanager
async def ftps_connection(
    host: str, password: str, user: str = "bblp", port: int = 990
) -> AsyncIterator[aioftp.Client]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    client = aioftp.Client(ssl=ctx)

    try:
        await client.connect(host, port=port)
        await client.login(user, password)
        yield client
    finally:
        await client.quit()
