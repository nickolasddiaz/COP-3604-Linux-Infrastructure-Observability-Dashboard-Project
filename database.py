#!/usr/bin/env python3
import asyncio
from typing import List
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asynctinydb


class TinyFluxDB:
    def __init__(self) -> None:
        db_path = Path('./database.json')
        self.db = asynctinydb.TinyDB(db_path)
        self.Record = asynctinydb.Query()
        self.mac_address_tag: str = "mac_address"
        self.time_zone = timezone.utc

    async def insert_data(self, mac_address: str, fields: dict) -> None:
        """Insert data into the database.

        Args:
            mac_address: the key to insert.
            fields: The dictionary to be inserted as the value.

        Returns:
            None: 
        """

        record = {
            self.mac_address_tag: mac_address,
            "timestamp": datetime.now(self.time_zone).isoformat(),
            "fields": fields,
        }
        await self.db.insert(record)

    async def query_data(self, macaddress: str, hours_past: int) -> List[dict]:
        """Search data into the database.
        
            Args:
                mac_address: the key to query.
                hours_past: How many hours to search for since now.
        
            Returns:
                List[dict]: The results of the query
        """
        hours_ago = (datetime.now(self.time_zone) - timedelta(hours=hours_past)).isoformat()
        records = await self.db.all()
        return [
            record
            for record in records
            if record[self.mac_address_tag] == macaddress
            and record["timestamp"] >= hours_ago
        ]

    async def get_mac_addresses(self) -> List[str]:
        """Get a list of mac addresses in the DB.
        
            Returns:
                List[dict]: Every mac address
        """
        records = await self.db.all()
        return sorted({record[self.mac_address_tag] for record in records})


if __name__ == "__main__": 
    db = TinyFluxDB()

    async def main() -> None:
        await db.insert_data("dummydata", {"test": 25, "test1": 30})
        print(await db.get_mac_addresses())
        print(await db.query_data("dummydata", 10))

    asyncio.run(main())