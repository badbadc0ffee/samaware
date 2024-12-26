import logging
from datetime import timezone
from functools import cached_property
from urllib.parse import urljoin

import requests


class WekanSyncer:
    """
    Allows synchronization of data from pretalx/SamAware to an external Wekan board.

    This performs a lot of caching without built-in invalidation, so it should be short- to medium-lived.
    Its lifetime must not exceed the validity duration of a Wekan auth token.
    """

    def __init__(self, wekan_server, username, password, board_id, initial_list_title,
                 initial_swimlane_title):
        """
        Creates a new WekanSyncer instance.

        Args:
          wekan_server: An instance of a WekanServer subclass
          username: Username for logging into Wekan
          password: Passwort for logging into Wekan
          board_id: Wekan ID of the Board to be synced to (e.g. taken from the Boards's URL in a browser)
          initial_list_title: Title/name of the Wekan List to which new Cards get added initially
          initial_swimlane_title: Title/name of the Wekan Swimlane to which new Cards get added initially
        """
        self.server = wekan_server
        self.username = username
        self.password = password
        self.initial_list_title = initial_list_title
        self.initial_swimlane_title = initial_swimlane_title

        self.board_path = f'api/boards/{board_id}/'
        self._card_lists = None

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    @cached_property
    def auth_token(self):
        data = {'username': self.username, 'password': self.password}
        try:
            response = self.server.post('users/login', data, None)
        except requests.RequestException:
            self.logger.error('Could not log into Wekan')
            raise

        self.logger.info('Logged into Wekan as "%s"', self.username)
        return response['token']

    @cached_property
    def user_id(self):
        """
        Wekan's internal ID of the logged-in user.
        """
        try:
            response = self.server.get('api/user', self.auth_token)
        except requests.RequestException:
            self.logger.error('Could not get user info from Wekan')
            raise
        return response['_id']

    @cached_property
    def list_ids(self):
        """
        Mapping from List title to ID for all Lists of the Wekan Board.
        """
        path = urljoin(self.board_path, 'lists')
        try:
            response = self.server.get(path, self.auth_token)
        except requests.RequestException:
            self.logger.error('Could not get Lists from Wekan')
            raise

        self.logger.info('Got all Lists from Wekan')
        return {l['title']: l['_id'] for l in response}

    @property
    def initial_list_id(self):
        try:
            return self.list_ids[self.initial_list_title]
        except KeyError as e:
            raise ValueError(f'Unknown Wekan List "{self.initial_list_title}"') from e

    @cached_property
    def swimlane_ids(self):
        """
        Mapping from Swimlane title to ID for all Swimlanes of the Wekan Board.
        """
        path = urljoin(self.board_path, 'swimlanes')
        try:
            response = self.server.get(path, self.auth_token)
        except requests.RequestException:
            self.logger.error('Could not get Swimlanes from Wekan')
            raise

        self.logger.info('Got all Swimlanes from Wekan')
        return {s['title']: s['_id'] for s in response}

    @property
    def initial_swimlane_id(self):
        try:
            return self.swimlane_ids[self.initial_swimlane_title]
        except KeyError as e:
            raise ValueError(f'Unknown Wekan Swimlane "{self.initial_swimlane_title}"') from e

    @cached_property
    def label_ids(self):
        """
        Mapping from Label title/name to ID for all Labels of the Wekan Board.
        """
        try:
            response = self.server.get(self.board_path, self.auth_token)
        except requests.RequestException:
            self.logger.error('Could not get Board/Label info from Wekan')
            raise

        self.logger.info('Got Board/Label info from Wekan')
        return {l['name']: l['_id'] for l in response['labels']}

    def id_for_label(self, title):
        if title not in self.label_ids:
            data = {'label': {'name': title, 'color': 'white'}}
            path = urljoin(self.board_path, 'labels')
            try:
                # This needs to be PUT as JSON, plain form data will not work
                self.server.put_json(path, data, self.auth_token)
            except requests.RequestException:
                self.logger.error('Could not add Label to Wekan')
                raise

            self.logger.info('Added label "%s" to Wekan', title)
            # No way to get the new ID from the response :-(

            # Invalidate cached labels
            del self.label_ids

        return self.label_ids[title]

    @property
    def card_lists(self):
        """
        Mapping from Card ID to List ID for all Cards of the Wekan Board.
        """
        if self._card_lists is None:
            mapping = {}
            for list_id in self.list_ids.values():
                path = urljoin(self.board_path, f'lists/{list_id}/cards')
                try:
                    response = self.server.get(path, self.auth_token)
                except requests.RequestException:
                    self.logger.error('Could not get Cards for list %s from Wekan', list_id)
                    raise

                for card in response:
                    mapping[card['_id']] = list_id

            self.logger.info('Got all Card from Wekan')
            self._card_lists = mapping

        return self._card_lists

    def get_card(self, card_id):
        try:
            list_id = self.card_lists[card_id]
        except KeyError as e:
            raise ValueError(f'Unknown card {card_id}') from e

        path = urljoin(self.board_path, f'lists/{list_id}/cards/{card_id}')
        try:
            response = self.server.get(path, self.auth_token)
        except requests.RequestException:
            self.logger.error('Could not get this Card from Wekan: %s', card_id)
            raise

        self.logger.info('Got this Card from Wekan: %s', card_id)
        return response

    def add_card(self, title, text, due_time, label_titles):
        data = self._make_card_data(title, text, due_time, label_titles)
        data['authorId'] = self.user_id
        data['swimlaneId'] = self.initial_swimlane_id

        path = urljoin(self.board_path, f'lists/{self.initial_list_id}/cards')
        try:
            response = self.server.post(path, data, self.auth_token)
        except requests.RequestException:
            self.logger.error('Could not add this Card to Wekan: "%s"', title)
            raise

        self.logger.info('Added this Card to Wekan: "%s"', title)

        card_id = response['_id']
        if self._card_lists is not None:
            self._card_lists[card_id] = self.initial_list_id

        # The Wekan API currently does not support setting "dueAt" and adding labels upon creation, but upon
        # editing
        self.update_card(card_id, due_time=due_time, label_titles=label_titles)

        return card_id

    def update_card(self, card_id, title=None, text=None, due_time=None, label_titles=None):
        old_data = self.get_card(card_id)
        target_data = self._make_card_data(title, text, due_time, label_titles)
        new_data = {}

        for key in ('title', 'description', 'dueAt'):
            if key in target_data and old_data.get(key) != target_data[key]:
                new_data[key] = target_data[key]

        if label_titles is not None:
            # We only ever add new labels, since we can't know which ones to remove
            new_label_ids = list(set(old_data.get('labelIds', []) + target_data['labelIds']))
            if new_label_ids != old_data.get('labelIds', []):
                new_data['labelIds'] = new_label_ids

        if not new_data:
            self.logger.info('Nothing changed, not updating this Card on Wekan: %s', card_id)
            return

        new_data['newBoardId'] = old_data['boardId']
        new_data['newListId'] = old_data['listId']
        new_data['newSwimlaneId'] = old_data['swimlaneId']

        list_id = old_data['listId']
        path = urljoin(self.board_path, f'lists/{list_id}/cards/{card_id}')
        try:
            self.server.put(path, new_data, self.auth_token)
        except requests.RequestException:
            self.logger.error('Could not update this Card on Wekan: %s', card_id)
            raise

        self.logger.info('Updated this Card on Wekan: %s', card_id)

    def _make_card_data(self, title=None, text=None, due_time=None, label_titles=None):
        data = {}

        if title is not None:
            data['title'] = title
        if text is not None:
            data['description'] = text
        if due_time is not None:
            due_time_utc = due_time.astimezone(timezone.utc)
            due_at_str = due_time_utc.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            data['dueAt'] = due_at_str
        if label_titles is not None:
            label_ids = [self.id_for_label(t) for t in label_titles]
            data['labelIds'] = label_ids

        return data


class WekanServer:

    def get(self, path, auth_token):
        raise NotImplementedError('get() must be implemented by the subclass')

    def post(self, path, data, auth_token):
        raise NotImplementedError('post() must be implemented by the subclass')

    def put(self, path, data, auth_token):
        raise NotImplementedError('put() must be implemented by the subclass')

    def put_json(self, path, obj, auth_token):
        raise NotImplementedError('put_json() must be implemented by the subclass')


class RealWekanServer(WekanServer):

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url

    def get(self, path, auth_token):
        response = requests.get(urljoin(self.base_url, path), headers=self._make_headers(auth_token),
                                timeout=10)
        response.raise_for_status()
        return response.json()

    def post(self, path, data, auth_token):
        response = requests.post(urljoin(self.base_url, path), data, headers=self._make_headers(auth_token),
                                 timeout=10)
        response.raise_for_status()
        return response.json()

    def put(self, path, data, auth_token):
        response = requests.put(urljoin(self.base_url, path), data, headers=self._make_headers(auth_token),
                                timeout=10)
        response.raise_for_status()
        return response.json()

    def put_json(self, path, obj, auth_token):
        response = requests.put(urljoin(self.base_url, path), json=obj,
                                headers=self._make_headers(auth_token), timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _make_headers(auth_token):
        headers = {'Accept': 'application/json', 'User-Agent': 'pretalx/SamAware Wekan Integration'}
        if auth_token is not None:
            headers['Authorization'] = f'Bearer {auth_token}'
        return headers
