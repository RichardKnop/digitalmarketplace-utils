from __future__ import absolute_import
import requests
import logging


logger = logging.getLogger(__name__)


class APIError(requests.HTTPError):
    def __init__(self, http_error):
        super(APIError, self).__init__(
            http_error,
            response=http_error.response,
            request=http_error.request)

    @property
    def response_message(self):
        try:
            return self.response.json()['error']
        except TypeError:
            return str(self.response.content)


class BaseAPIClient(object):
    def __init__(self, base_url=None, auth_token=None, enabled=True):
        self.base_url = base_url
        self.auth_token = auth_token
        self.enabled = enabled

    def _put(self, url, data):
        return self._request("PUT", url, data=data)

    def _get(self, url, params=None):
        return self._request("GET", url, params=params)

    def _post(self, url, data):
        return self._request("POST", url, data=data)

    def _request(self, method, url, data=None, params=None):
        if not self.enabled:
            return None
        try:
            logger.debug("API request %s %s", method, url)
            headers = {
                "Content-type": "application/json",
                "Authorization": "Bearer {}".format(self.auth_token),
            }
            response = requests.request(
                method, url,
                headers=headers, json=data, params=params)
            response.raise_for_status()

            return response.json()
        except requests.HTTPError as e:
            raise APIError(e)
        except requests.RequestException as e:
            logger.exception(e.message)
            raise


class SearchAPIClient(BaseAPIClient):
    FIELDS = [
        "lot",
        "serviceName",
        "serviceSummary",
        "serviceBenefits",
        "serviceFeatures",
        "serviceTypes",
        "supplierName",
    ]

    def init_app(self, app):
        self.base_url = app.config['DM_SEARCH_API_URL']
        self.auth_token = app.config['DM_SEARCH_API_AUTH_TOKEN']
        self.enabled = app.config['ES_ENABLED']

    def _url(self, path):
        return "{}/g-cloud/services{}".format(self.base_url, path)

    def index(self, service_id, service, supplier_name):
        url = self._url("/{}".format(service_id))
        data = self._convert_service(service_id, service, supplier_name)

        return self._put(url, data=data)

    def search(self, payload):
        url = self._url("/search")
        return self._get(url, payload)

    def _convert_service(self, service_id, service, supplier_name):
        data = {k: service[k] for k in self.FIELDS if k in service}
        data['supplierName'] = supplier_name
        data['id'] = service_id

        return {
            "service": data
        }


class DataAPIClient(BaseAPIClient):
    def init_app(self, app):
        self.base_url = app.config['DM_DATA_API_URL']
        self.auth_token = app.config['DM_DATA_API_AUTH_TOKEN']

    def get_service(self, service_id):
        return self._get(
            "{}/services/{}".format(self.base_url, service_id))['services']

    def find_service(self, supplier_id=None, page=None):
        params = {}
        if supplier_id is not None:
            params['supplier_id'] = supplier_id
        if page is not None:
            params['page'] = page

        return self._get(
            self.base_url + "/services",
            params=params)['services']

    def update_service(self, service_id, service, user, reason):
        return self._post(
            "{}/services/{}".format(self.base_url, service_id),
            data={
                "update_details": {
                    "updated_by": user,
                    "update_reason": reason,
                },
                "services": service,
            })
