import asyncio
import json
import pathlib
from collections import defaultdict
from datetime import date, datetime, timedelta
import gzip


import logging
logging.getLogger("httpx").setLevel(logging.WARNING)


import httpx
import tqdm
import tqdm.asyncio

# import sys
# import time  # Optional: Just to simulate delay for testing
import pandas as pd
import os


from nepse.DummyIDUtils import AsyncDummyIDManager, DummyIDManager
from nepse.Errors import (
    NepseInvalidClientRequest,
    NepseInvalidServerResponse,
    NepseNetworkError,
    NepseTokenExpired,
)
from nepse.TokenUtils import AsyncTokenManager, TokenManager


class _Nepse:
    def __init__(self, token_manager, dummy_id_manager):

        self.token_manager = token_manager(self)

        self.dummy_id_manager = dummy_id_manager(
            market_status_function=self.getMarketStatus,
            date_function=datetime.now,
        )
        # explicitly set value to True, can be disabled by user using setTLSVerification method
        self._tls_verify = True
        # list of all company that were listed in nepse (including delisted but doesn't include promoter shares)
        self.company_symbol_id_keymap = None
        # list of all valid company that are not delisted (includes promoter share)
        self.security_symbol_id_keymap = None

        self.company_list = None
        self.security_list = None
        self.price_history = None
        self.sector_scrips = None

        self.floor_sheet_size = 500

        self.base_url = "https://www.nepalstock.com"
        
        # Get the folder where THIS file (module) is located
        # directory of the current file
        file_dir = os.path.dirname(os.path.abspath(__file__))
        
        # go one level up
        parent_dir = os.path.dirname(file_dir)
        
        # go into "example" directory
        self.base_dir = os.path.join(parent_dir, "Data")

        self.load_json_api_end_points()
        self.load_json_dummy_data()
        self.load_json_header()

    ############################################### PRIVATE METHODS###############################################
    def getDummyID(self):
        return self.dummy_id_manager.getDummyID()

    def load_json_header(self):
        json_file_path = f"{pathlib.Path(__file__).parent}/data/HEADERS.json"
        with open(json_file_path, "r") as json_file:
            self.headers = json.load(json_file)
            self.headers["Host"] = self.base_url.replace("https://", "")
            self.headers["Referer"] = self.base_url.replace("https://", "")

    def load_json_api_end_points(self):
        json_file_path = f"{pathlib.Path(__file__).parent}/data/API_ENDPOINTS.json"
        with open(json_file_path, "r") as json_file:
            self.api_end_points = json.load(json_file)

    def get_full_url(self, api_url):
        return f"{self.base_url}{api_url}"

    def load_json_dummy_data(self):
        json_file_path = f"{pathlib.Path(__file__).parent}/data/DUMMY_DATA.json"
        with open(json_file_path, "r") as json_file:
            self.dummy_data = json.load(json_file)

    def getDummyData(self):
        return self.dummy_data

    def init_client(self, tls_verify):
        pass

    def requestGETAPI(self, url):
        pass

    def requestPOSTAPI(self, url, payload_generator):
        pass

    # These 3 functions maybe both sync/async which needs to be implemented by the the child class
    def getPOSTPayloadIDForScrips(self):
        pass

    def getPOSTPayloadID(self):
        pass

    def getPOSTPayloadIDForFloorSheet(self):
        pass

    def handle_response(self, response):
        match response.status_code:
            case status if 200 <= status < 300:
                return response.json()

            case 400:
                raise NepseInvalidClientRequest()

            case 401:  # access token expired
                raise NepseTokenExpired()

            case 502:
                raise NepseInvalidServerResponse()

            case _:
                raise NepseNetworkError()

    ############################################### PUBLIC METHODS###############################################
    def setTLSVerification(self, flag):
        self._tls_verify = flag
        self.init_client(tls_verify=flag)

    # api requiring get method
    def getMarketStatus(self):
        return self.requestGETAPI(url=self.api_end_points["nepse_open_url"])

    def getPriceVolume(self):
        return self.requestGETAPI(url=self.api_end_points["price_volume_url"])

    def getSummary(self):
        return self.requestGETAPI(url=self.api_end_points["summary_url"])

    def getTopTenTradeScrips(self):
        return self.requestGETAPI(url=self.api_end_points["top_ten_trade_url"])

    def getTopTenTransactionScrips(self):
        return self.requestGETAPI(url=self.api_end_points["top_ten_transaction_url"])

    def getTopTenTurnoverScrips(self):
        return self.requestGETAPI(url=self.api_end_points["top_ten_turnover_url"])

    def getSupplyDemand(self):
        return self.requestGETAPI(url=self.api_end_points["supply_demand_url"])

    def getTopGainers(self):
        return self.requestGETAPI(url=self.api_end_points["top_gainers_url"])

    def getTopLosers(self):
        return self.requestGETAPI(url=self.api_end_points["top_losers_url"])

    def isNepseOpen(self):
        return self.requestGETAPI(url=self.api_end_points["nepse_open_url"])

    def getNepseIndex(self):
        return self.requestGETAPI(url=self.api_end_points["nepse_index_url"])

    def getNepseSubIndices(self):
        return self.requestGETAPI(url=self.api_end_points["nepse_subindices_url"])

    def getLiveMarket(self):
        return self.requestGETAPI(url=self.api_end_points["live-market"])

    # api requiring post method

        
        

    def getDailyNepseIndexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["nepse_index_daily_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailySensitiveIndexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["sensitive_index_daily_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyFloatIndexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["float_index_daily_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailySensitiveFloatIndexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["sensitive_float_index_daily_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyBankSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["banking_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyDevelopmentBankSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["development_bank_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyFinanceSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["finance_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyHotelTourismSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["hotel_tourism_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyHydroSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["hydro_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyInvestmentSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["investment_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyLifeInsuranceSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["life_insurance_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyManufacturingSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["manufacturing_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyMicrofinanceSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["microfinance_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyMutualfundSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["mutual_fund_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyNonLifeInsuranceSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["non_life_insurance_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyOthersSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["others_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )

    def getDailyTradingSubindexGraph(self):
        return self.requestPOSTAPI(
            url=self.api_end_points["trading_sub_index_graph"],
            payload_generator=self.getPOSTPayloadID,
        )


class AsyncNepse(_Nepse):
    def __init__(self):
        super().__init__(AsyncTokenManager, AsyncDummyIDManager)
        # internal flag to set tls verification true or false during http request
        self.init_client(tls_verify=self._tls_verify)

    ############################################### PRIVATE METHODS###############################################
    async def getPOSTPayloadIDForScrips(self):
        dummy_id = await self.getDummyID()
        e = self.getDummyData()[dummy_id] + dummy_id + 2 * (date.today().day)
        return e

    async def getPOSTPayloadID(self):
        e = await self.getPOSTPayloadIDForScrips()
        # we need to await before update is completed
        await self.token_manager.update_completed.wait()
        post_payload_id = (
            e
            + self.token_manager.salts[3 if e % 10 < 5 else 1] * date.today().day
            - self.token_manager.salts[(3 if e % 10 < 5 else 1) - 1]
        )
        return post_payload_id

    async def getPOSTPayloadIDForFloorSheet(self):
        e = await self.getPOSTPayloadIDForScrips()

        # we need to await before update is completed
        await self.token_manager.update_completed.wait()

        post_payload_id = (
            e
            + self.token_manager.salts[1 if e % 10 < 4 else 3] * date.today().day
            - self.token_manager.salts[(1 if e % 10 < 4 else 3) - 1]
        )
        return post_payload_id

    async def getAuthorizationHeaders(self):
        headers = self.headers
        access_token = await self.token_manager.getAccessToken()

        headers = {
            "Authorization": f"Salter {access_token}",
            "Content-Type": "application/json",
            **self.headers,
        }

        return headers

    def init_client(self, tls_verify):
        self.client = httpx.AsyncClient(verify=tls_verify, http2=False, timeout=100)

    async def requestGETAPI(self, url, include_authorization_headers=True):
        try:
            response = await self.client.get(
                self.get_full_url(api_url=url),
                headers=(
                    await self.getAuthorizationHeaders()
                    if include_authorization_headers
                    else self.headers
                ),
            )
            return self.handle_response(response)
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError):
            return await self.requestGETAPI(url, include_authorization_headers)
        except NepseTokenExpired:
            await self.token_manager.update()
            return await self.requestGETAPI(url, include_authorization_headers)

    async def requestPOSTAPI(self, url, payload_generator):
        try:
            response = await self.client.post(
                self.get_full_url(api_url=url),
                headers=await self.getAuthorizationHeaders(),
                data=json.dumps({"id": await payload_generator()}),
            )
            return self.handle_response(response)
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError):
            return await self.requestPOSTAPI(url, payload_generator)
        except NepseTokenExpired:
            await self.token_manager.update()
            return await self.requestPOSTAPI(url, payload_generator)

    ############################################### PUBLIC METHODS###############################################
    # api requiring get method
    async def getCompanyList(self):
        self.company_list = await self.requestGETAPI(
            url=self.api_end_points["company_list_url"]
        )
        # return a copy of self.company_list so than changes after return are not perisistent
        return list(self.company_list)

    async def getSecurityList(self):
        self.security_list = await self.requestGETAPI(
            url=self.api_end_points["security_list_url"]
        )
        # return a copy of self.company_list so than changes after return are not perisistent
        return list(self.security_list)
    
    async def getCompanyPriceHisotry(self, symbol):
        symbol = symbol.upper()
        company_id = (await self.getSecurityIDKeyMap())[symbol]

        self.price_history = await self.requestGETAPI(
            url=f"{self.api_end_points['price_history']}{company_id}"
        )
        # return a copy of self.company_list so than changes after return are not perisistent
        return list(self.price_history)
    
        
        
        
        
        

    async def getSectorScrips(self):
        if self.sector_scrips is None:
            company_info_dict = {
                company_info["symbol"]: company_info
                for company_info in (await self.getCompanyList())
            }
            sector_scrips = defaultdict(list)

            for security_info in await self.getSecurityList():
                symbol = security_info["symbol"]
                if company_info_dict.get(symbol):
                    company_info = company_info_dict[symbol]
                    sector_name = company_info["sectorName"]
                    sector_scrips[sector_name].append(symbol)
                else:
                    sector_scrips["Promoter Share"].append(symbol)

            self.sector_scrips = dict(sector_scrips)
        # return a copy of self.sector_scrips so than changes after return are not perisistent
        return dict(self.sector_scrips)

    async def getCompanyIDKeyMap(self, force_update=False):
        if self.company_symbol_id_keymap is None or force_update:
            company_list = await self.getCompanyList()
            self.company_symbol_id_keymap = {
                company["symbol"]: company["id"] for company in company_list
            }
        return self.company_symbol_id_keymap

    async def getSecurityIDKeyMap(self, force_update=False):
        if self.security_symbol_id_keymap is None or force_update:
            security_list = await self.getSecurityList()
            self.security_symbol_id_keymap = {
                security["symbol"]: security["id"] for security in security_list
            }
        return self.security_symbol_id_keymap

    async def getCompanyPriceVolumeHistory(
        self, symbol, start_date=None, end_date=None
    ):
        end_date = end_date if end_date else date.today()
        start_date = start_date if start_date else (end_date - timedelta(days=365))
        symbol = symbol.upper()
        company_id = (await self.getSecurityIDKeyMap())[symbol]
        url = f"{self.api_end_points['company_price_volume_history']}{company_id}?&size=500&startDate={start_date}&endDate={end_date}"
        return (await self.requestGETAPI(url=url))["content"]

    async def getNotices(self):
        url=f"{self.api_end_points['notice']}"
        return self.requestGETAPI(url=url)
    
    async def getCorp_Disclosure(self):
        url=f"{self.api_end_points['corporatedisclosures']}"
        return self.requestGETAPI(url=url)

    async def getListedCompanies(self):
        url = f"{self.api_end_points['listed_companies']}"
        return self.requestGETAPI(url=url)
    async def getDateWiseIndex(self,show_progress=True):
        url = f"{self.api_end_points['date_wise_Index']}"
  
        # Read the first case
        sheet = self.requestGETAPI(url=url)
        
        history_sheets = sheet["content"]
        max_page = sheet["totalPages"]
        page_range = (
            tqdm.tqdm(range(1, max_page)) if show_progress else range(1, max_page)
        )
        for page_number in page_range:
            url2 = f"{url}?page={page_number}"
            current_sheet = self.requestGETAPI(url=url2)
            current_sheet_content = current_sheet["content"]
            history_sheets.extend(current_sheet_content)
        return history_sheets














    # api requiring post method
    async def getDailyScripPriceGraph(self, symbol):
        symbol = symbol.upper()
        company_id = (await self.getSecurityIDKeyMap())[symbol]
        return await self.requestPOSTAPI(
            url=f"{self.api_end_points['company_daily_graph']}{company_id}",
            payload_generator=self.getPOSTPayloadIDForScrips,
        )

    async def getCompanyDetails(self, symbol):
        symbol = symbol.upper()
        company_id = (await self.getSecurityIDKeyMap())[symbol]
        return await self.requestPOSTAPI(
            url=f"{self.api_end_points['company_details']}{company_id}",
            payload_generator=self.getPOSTPayloadIDForScrips,
        )
    
    


    async def getFloorSheet(self, show_progress=False):

        url = f"{self.api_end_points['floor_sheet']}?&size={self.floor_sheet_size}&sort=contractId,desc"
        sheet = await self.requestPOSTAPI(
            url=url, payload_generator=self.getPOSTPayloadIDForFloorSheet
        )
        floor_sheets = sheet["floorsheets"]["content"]
        max_page = sheet["floorsheets"]["totalPages"]

        # page 0 is already downloaded so starting from 1
        page_range = range(1, max_page)
        awaitables = map(
            lambda page_number: self._getFloorSheetPageNumber(
                url,
                page_number,
            ),
            page_range,
        )
        if show_progress:
            remaining_floor_sheets = await tqdm.asyncio.tqdm.gather(*awaitables)
        else:
            remaining_floor_sheets = await asyncio.gather(*awaitables)

        floor_sheets = [floor_sheets] + remaining_floor_sheets
        return [row for array in floor_sheets for row in array]

    async def _getFloorSheetPageNumber(self, url, page_number):
        current_sheet = await self.requestPOSTAPI(
            url=f"{url}&page={page_number}",
            payload_generator=self.getPOSTPayloadIDForFloorSheet,
        )
        current_sheet_content = (
            current_sheet["floorsheets"]["content"] if current_sheet else []
        )
        return current_sheet_content

    async def getFloorSheetOf(self, symbol, business_date=None):
        # business date can be YYYY-mm-dd string or date object
        symbol = symbol.upper()
        company_id = (await self.getSecurityIDKeyMap())[symbol]
        business_date = (
            date.fromisoformat(f"{business_date}") if business_date else date.today()
        )
        url = f"{self.api_end_points['company_floorsheet']}{company_id}?&businessDate={business_date}&size={self.floor_sheet_size}&sort=contractid,desc"
        sheet = await self.requestPOSTAPI(
            url=url, payload_generator=self.getPOSTPayloadIDForFloorSheet
        )
        if sheet:  # sheet might be empty
            floor_sheets = sheet["floorsheets"]["content"]
            for page in range(1, sheet["floorsheets"]["totalPages"]):
                next_sheet = await self.requestPOSTAPI(
                    url=f"{url}&page={page}",
                    payload_generator=self.getPOSTPayloadIDForFloorSheet,
                )
                next_floor_sheet = next_sheet["floorsheets"]["content"]
                floor_sheets.extend(next_floor_sheet)
        else:
            floor_sheets = []
        return floor_sheets

    async def getSymbolMarketDepth(self, symbol):
        # First check if market is open
        market_status = await self.isNepseOpen()  # Assuming this is also async
        
        if market_status['isOpen'] == 'OPEN':
            symbol = symbol.upper()
            company_id_map = await self.getSecurityIDKeyMap()
            company_id = company_id_map[symbol]
            url = f"{self.api_end_points['market-depth']}{company_id}/"
            return await self.requestGETAPI(url=url)
        else:
            print(f"Market is {market_status['isOpen']} as of {market_status['asOf']}")
            return {
                'status': 'market_closed',
                'message': f"NEPSE market is currently {market_status['isOpen']}",
                'timestamp': market_status['asOf'],
                'requested_symbol': symbol.upper()
            }


class Nepse(_Nepse):
    def __init__(self):
        super().__init__(TokenManager, DummyIDManager)
        # internal flag to set tls verification true or false during http request
        self.init_client(tls_verify=self._tls_verify)

    ############################################### PRIVATE METHODS###############################################
    def getPOSTPayloadIDForScrips(self):
        dummy_id = self.getDummyID()
        e = self.getDummyData()[dummy_id] + dummy_id + 2 * (date.today().day)
        return e

    def getPOSTPayloadID(self):
        e = self.getPOSTPayloadIDForScrips()
        post_payload_id = (
            e
            + self.token_manager.salts[3 if e % 10 < 5 else 1] * date.today().day
            - self.token_manager.salts[(3 if e % 10 < 5 else 1) - 1]
        )
        return post_payload_id

    def getPOSTPayloadIDForFloorSheet(self):
        e = self.getPOSTPayloadIDForScrips()
        post_payload_id = (
            e
            + self.token_manager.salts[1 if e % 10 < 4 else 3] * date.today().day
            - self.token_manager.salts[(1 if e % 10 < 4 else 3) - 1]
        )
        return post_payload_id

    def getAuthorizationHeaders(self):
        headers = self.headers
        access_token = self.token_manager.getAccessToken()

        headers = {
            "Authorization": f"Salter {access_token}",
            "Content-Type": "application/json",
            **self.headers,
        }

        return headers

    def init_client(self, tls_verify):
        self.client = httpx.Client(verify=tls_verify, http2=True, timeout=100)

    def requestGETAPI(self, url, include_authorization_headers=True):
        try:
            response = self.client.get(
                self.get_full_url(api_url=url),
                headers=(
                    self.getAuthorizationHeaders()
                    if include_authorization_headers
                    else self.headers
                ),
            )
            return self.handle_response(response)
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError):
            return self.requestGETAPI(url, include_authorization_headers)
        except NepseTokenExpired:
            self.token_manager.update()
            return self.requestGETAPI(url)

    def requestPOSTAPI(self, url, payload_generator):
        try:
            response = self.client.post(
                self.get_full_url(api_url=url),
                headers=self.getAuthorizationHeaders(),
                data=json.dumps({"id": payload_generator()}),
            )
            return self.handle_response(response)
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError):
            return self.requestPOSTAPI(url, payload_generator)
        except NepseTokenExpired:
            self.token_manager.update()
            return self.requestPOSTAPI(url, payload_generator)

    ############################################### PUBLIC METHODS###############################################
    # api requiring get method
    def getCompanyList(self):
        self.company_list = self.requestGETAPI(
            url=self.api_end_points["company_list_url"]
        )
        # return a copy of self.company_list so than changes after return are not perisistent
        return list(self.company_list)

    def getSecurityList(self):
        self.security_list = self.requestGETAPI(
            url=self.api_end_points["security_list_url"]
        )
        # return a copy of self.company_list so than changes after return are not perisistent
        return list(self.security_list)

    def getSectorScrips(self):
        if self.sector_scrips is None:
            company_info_dict = {
                company_info["symbol"]: company_info
                for company_info in self.getCompanyList()
            }
            sector_scrips = defaultdict(list)

            for security_info in self.getSecurityList():
                symbol = security_info["symbol"]
                if company_info_dict.get(symbol):
                    company_info = company_info_dict[symbol]
                    sector_name = company_info["sectorName"]
                    sector_scrips[sector_name].append(symbol)
                else:
                    sector_scrips["Promoter Share"].append(symbol)

            self.sector_scrips = dict(sector_scrips)
        # return a copy of self.sector_scrips so than changes after return are not perisistent
        return dict(self.sector_scrips)

    def getCompanyIDKeyMap(self, force_update=False):
        if self.company_symbol_id_keymap is None or force_update:
            company_list = self.getCompanyList()
            self.company_symbol_id_keymap = {
                company["symbol"]: company["id"] for company in company_list
            }
        return self.company_symbol_id_keymap





    def getNotices(self):
        url=f"{self.api_end_points['notice']}"
        # print(url)
        return self.requestGETAPI(url=url)

    def getCorp_Disclosure(self):
        url=f"{self.api_end_points['corporatedisclosures']}"
        # print(url)
        return self.requestGETAPI(url=url)


    def getSecurityIDKeyMap(self, force_update=False):
        if self.security_symbol_id_keymap is None or force_update:
            security_list = self.getSecurityList()
            self.security_symbol_id_keymap = {
                security["symbol"]: security["id"] for security in security_list
            }
        return self.security_symbol_id_keymap

    def getCompanyPriceVolumeHistory(self, symbol, start_date=None, end_date=None):
        end_date = end_date if end_date else date.today()
        start_date = start_date if start_date else (end_date - timedelta(days=365))
        symbol = symbol.upper()
        company_id = self.getSecurityIDKeyMap()[symbol]
        url = f"{self.api_end_points['company_price_volume_history']}{company_id}?&size=500&startDate={start_date}&endDate={end_date}"
        return self.requestGETAPI(url=url)


    def getListedCompanies(self):
        url = f"{self.api_end_points['listed_companies']}"
        return self.requestGETAPI(url=url)
    
    def getDateWiseIndex(self,show_progress=True):
        url = f"{self.api_end_points['date_wise_Index']}"
  
        # Read the first case
        sheet = self.requestGETAPI(url=url)
        
        history_sheets = sheet["content"]
        max_page = sheet["totalPages"]
        page_range = (
            tqdm.tqdm(range(1, max_page)) if show_progress else range(1, max_page)
        )
        for page_number in page_range:
            url2 = f"{url}?page={page_number}"
            current_sheet = self.requestGETAPI(url=url2)
            current_sheet_content = current_sheet["content"]
            history_sheets.extend(current_sheet_content)
        return history_sheets



    def getCompanyPriceHisotry(self, symbol, show_progress=False):
        symbol = symbol.upper()
        try:
            company_id = self.getSecurityIDKeyMap()[symbol]
            url = f"{self.api_end_points['price_history']}{company_id}"
            
            # print(url)
            # print(company_id)
            # return self.requestGETAPI(url=url)
        
            # Read the first case
            sheet = self.requestGETAPI(url=url)
            
            history_sheets = sheet["content"]
            max_page = sheet["totalPages"]
            page_range = (
                tqdm.tqdm(range(1, max_page)) if show_progress else range(1, max_page)
            )
            for page_number in page_range:
                url2 = f"{url}?page={page_number}"
                # print(url2)
                current_sheet = self.requestGETAPI(url=url2)
                
                # current_sheet = self.requestPOSTAPI(
                #     url=f"{url}&page={page_number}",
                #     payload_generator=self.getPOSTPayloadIDForFloorSheet,
                # )
                current_sheet_content = current_sheet["content"]
                history_sheets.extend(current_sheet_content)
            return history_sheets
        except Exception as e:
            print(f"An error occurred: {e}")
            return {}
        
    
    
    
    
    
    
    
    
    
    



    # api requiring post method
    def getDailyScripPriceGraph(self, symbol):
        symbol = symbol.upper()
        company_id = self.getSecurityIDKeyMap()[symbol]
        return self.requestPOSTAPI(
            url=f"{self.api_end_points['company_daily_graph']}{company_id}",
            payload_generator=self.getPOSTPayloadIDForScrips,
        )

    def getCompanyDetails(self, symbol):
        symbol = symbol.upper()
        company_id = self.getSecurityIDKeyMap()[symbol]
        return self.requestPOSTAPI(
            url=f"{self.api_end_points['company_details']}{company_id}",
            payload_generator=self.getPOSTPayloadIDForScrips,
        )
    


    def getPriceVolumeHistory(self, business_date=None,show_progress=True):
        # url = f"{self.api_end_points['todays_price']}?&size=500&businessDate={business_date}"
        url = f"{self.api_end_points['todays_price']}"
        # print(url)
        # return self.requestPOSTAPI(
        #     url=url, payload_generator=self.getPOSTPayloadIDForFloorSheet
        # )

        
        sheet = self.requestPOSTAPI(
            url=url, payload_generator=self.getPOSTPayloadIDForFloorSheet
        )
        vs_sheet = sheet["content"]
        max_page = sheet["totalPages"]
        # max_page = 1
        p_size = sheet["size"]
        # print(max_page)
        page_range = (
            tqdm.tqdm(range(1, max_page)) if show_progress else range(1, max_page)
        )
        for page_number in page_range:
            current_sheet = self.requestPOSTAPI(
                url=f"{url}?page={page_number}&size={p_size}",
                payload_generator=self.getPOSTPayloadIDForFloorSheet,
            )
            current_sheet_content = current_sheet["content"]
            # print(current_sheet_content)
            vs_sheet.extend(current_sheet_content)
            
            
        return vs_sheet     
            
            
            

    # Nepse Floorsheet is extracted here
    


    def getFloorSheet(self, Type='list',show_progress=True ):
        """
        Get floor sheet data and save in appropriate format
        
        Parameters:
            show_progress (bool): Whether to show progress bar
            Type (str): Output type - 
                       'list' (default): saves as JSON, returns raw data
                       'xlsx': saves as Excel, returns file path
        
        Returns:
            list: Floor sheet data when Type='list'
            str: File path when Type='xlsx'
        """
        
        # Create a 'floorsheet' folder inside that
        floorsheet_dir = os.path.join(self.base_dir, "floorsheet")
        os.makedirs(floorsheet_dir, exist_ok=True)
        
        # Ensure 'floorsheet' directory exists
        #floorsheet_dir = os.makedirs("floorsheet", exist_ok=True)
    
        url = f"{self.api_end_points['floor_sheet']}?&size={self.floor_sheet_size}&sort=contractId,desc"
        
        sheet = self.requestPOSTAPI(
            url=url, payload_generator=self.getPOSTPayloadIDForFloorSheet
        )
        
        # Clean first page
        floor_sheets = sheet["floorsheets"]["content"]
        
        for row in floor_sheets:
            row.pop("securityName", None)
        
        max_page = sheet["floorsheets"]["totalPages"]
        
        page_range = tqdm.tqdm(range(1, max_page), desc="Downloading Floorsheet") if show_progress else range(1, max_page)
        
        for page_number in page_range:
            current_sheet = self.requestPOSTAPI(
                url=f"{url}&page={page_number}",
                payload_generator=self.getPOSTPayloadIDForFloorSheet,
            )
        
            content = current_sheet["floorsheets"]["content"]
        
            # Remove key before extending
            for row in content:
                row.pop("securityName", None)
        
            floor_sheets.extend(content)
        
        # Get business date for filename
        business_date = floor_sheets[0]['businessDate'] if floor_sheets else "unknown_date"
        
        if Type.lower() == 'xlsx':
            # Save as Excel
            try:
                df = pd.DataFrame(floor_sheets)
                file_path = os.path.join(floorsheet_dir, f"{business_date}.xlsx")
                # file_path = f"floorsheet/{business_date}.xlsx"
                df.to_excel(file_path, index=False)
                print(f"Data saved successfully to {file_path}")
                return file_path
            except Exception as e:
                print(f"Error saving Excel file: {str(e)}")
                return None
        else:
            # Default case (Type='list') - save as JSON
            # try:
            #     # file_path = f"floorsheet/{business_date}.json"
            #     file_path = os.path.join(floorsheet_dir, f"{business_date}.json")
            #     with open(file_path, 'w') as f:
            #         json.dump(floor_sheets, f, indent=4)
            #     print(f"Data saved successfully to {file_path}")
            #     return floor_sheets
            # except Exception as e:
            #     print(f"Error saving JSON file: {str(e)}")
            #     return None
            
            try:
                file_path = os.path.join(floorsheet_dir, f"{business_date}.json.gz")
            
                with gzip.open(file_path, "wt", encoding="utf-8") as f:
                    json.dump(floor_sheets, f, separators=(",", ":"))  # no indent = smaller
                
                file_path_uc = os.path.join(self.base_dir, "latest.json")
                with open(file_path_uc, 'w') as f:
                    json.dump(floor_sheets, f, indent=4)  
                    
                    
                    
                print(f"Compressed data saved to {file_path}")
                return floor_sheets
            
            except Exception as e:
                print(f"Error saving gzip JSON file: {str(e)}")
                return None            

    def getFloorSheetOf(self, symbol, business_date=None):
            # business date can be YYYY-mm-dd string or date object
            symbol = symbol.upper()
            company_id = self.getSecurityIDKeyMap()[symbol]
            business_date = (
                date.fromisoformat(f"{business_date}") if business_date else date.today()
            )
            url = f"{self.api_end_points['company_floorsheet']}{company_id}?&businessDate={business_date}&size={self.floor_sheet_size}&sort=contractid,desc"
            sheet = self.requestPOSTAPI(
                url=url, payload_generator=self.getPOSTPayloadIDForFloorSheet
            )
            if sheet:  # sheet might be empty
                floor_sheets = sheet["floorsheets"]["content"]
                for page in range(1, sheet["floorsheets"]["totalPages"]):
                    next_sheet = self.requestPOSTAPI(
                        url=f"{url}&page={page}",
                        payload_generator=self.getPOSTPayloadIDForFloorSheet,
                    )
                    next_floor_sheet = next_sheet["floorsheets"]["content"]
                    floor_sheets.extend(next_floor_sheet)
            else:
                floor_sheets = []
            return floor_sheets











    def getSymbolMarketDepth(self, symbol):
        # Check if NEPSE is open
        market_status = self.isNepseOpen()
        
        if market_status['isOpen'] == 'OPEN':
            symbol = symbol.upper()
            company_id = self.getSecurityIDKeyMap()[symbol]
            url = f"{self.api_end_points['market-depth']}{company_id}/"
            return self.requestGETAPI(url)
        else:
            print(f"Market is {market_status['isOpen']} as of {market_status['asOf']}")
            return {
                'status': 'market_closed',
                'message': f"NEPSE market is currently {market_status['isOpen']}",
                'timestamp': market_status['asOf'],
                'requested_symbol': symbol
            }
