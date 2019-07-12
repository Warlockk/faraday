"""
Faraday Penetration Test IDE
Copyright (C) 2019  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information
"""
import mock

from faraday.server.api.modules.agent import AgentView
from faraday.server.models import Agent
from tests.factories import AgentFactory, WorkspaceFactory
from tests.test_api_workspaced_base import ReadOnlyAPITests
from tests import factories


def http_req(method, client, endpoint, json_dict, expected_status_codes, follow_redirects=False):
    res = ""
    if method.upper() == "GET":
        res = client.get(endpoint, json=json_dict, follow_redirects=follow_redirects)
    elif method.upper() == "POST":
        res = client.post(endpoint, json=json_dict, follow_redirects=follow_redirects)
    elif method.upper() == "PUT":
        res = client.put(endpoint, json=json_dict, follow_redirects=follow_redirects)
    assert res.status_code in expected_status_codes
    return res


def logout(client, expected_status_codes):
    res = http_req(method="GET",
                   client=client,
                   endpoint="/logout",
                   json_dict=dict(),
                   expected_status_codes=expected_status_codes)
    return res


class TestAgentCreationAPI():

    @mock.patch('faraday.server.api.modules.agent.faraday_server')
    def test_create_agent_valid_token(self, faraday_server_config, test_client, session):
        faraday_server_config.agent_token = 'sarasa'
        workspace = WorkspaceFactory.create(name='test')
        session.add(workspace)
        logout(test_client, [302])
        initial_agent_count = len(session.query(Agent).all())
        raw_data = {"token": 'sarasa'}
        # /v2/ws/<workspace_name>/agent_registration/
        res = test_client.post('/v2/ws/{0}/agent_registration/'.format(workspace.name), data=raw_data)
        assert res.status_code == 201
        assert len(session.query(Agent).all()) == initial_agent_count + 1

    @mock.patch('faraday.server.api.modules.agent.faraday_server')
    def test_create_agent_invalid_token(self, faraday_server_config, test_client, session):
        faraday_server_config.agent_token = 'sarasa'
        workspace = WorkspaceFactory.create(name='test')
        session.add(workspace)
        logout(test_client, [302])
        raw_data = {"token": 'INVALID'}
        # /v2/ws/<workspace_name>/agent_registration/
        res = test_client.post('/v2/ws/{0}/agent_registration/'.format(workspace.name), data=raw_data)
        assert res.status_code == 401

    @mock.patch('faraday.server.api.modules.agent.faraday_server')
    def test_create_agent_agent_token_not_set(self, faraday_server_config, test_client, session):
        faraday_server_config.agent_token = None
        workspace = WorkspaceFactory.create(name='test')
        session.add(workspace)
        logout(test_client, [302])
        raw_data = {"token": 'INVALID'}
        # /v2/ws/<workspace_name>/agent_registration/
        res = test_client.post('/v2/ws/{0}/agent_registration/'.format(workspace.name), data=raw_data)
        assert res.status_code == 401

    @mock.patch('faraday.server.api.modules.agent.faraday_server')
    def test_create_agent_invalid_payload(self, faraday_server_config, test_client, session):
        faraday_server_config.agent_token = None
        workspace = WorkspaceFactory.create(name='test')
        session.add(workspace)
        logout(test_client, [302])
        raw_data = {"PEPE": 'INVALID'}
        # /v2/ws/<workspace_name>/agent_registration/
        res = test_client.post('/v2/ws/{0}/agent_registration/'.format(workspace.name), data=raw_data)
        assert res.status_code == 400


class TestAgentAPIGeneric(ReadOnlyAPITests):
    model = Agent
    factory = factories.AgentFactory
    view_class = AgentView
    api_endpoint = 'agent'

    def create_raw_agent(self, _type='shared', status="offline", token="TOKEN"):
        return {
            "projects": 1,
            "type": _type,
            "version": "1",
            "token": token,
            "status": status,
            "jobs": 1,
            "description": "My Desc"
        }

    def test_create_agent_invalid(self, test_client, session):
        initial_agent_count = len(session.query(Agent).all())
        raw_agent = self.create_raw_agent()
        res = test_client.post(self.url(), data=raw_agent)
        assert res.status_code == 405  # the only way to create agents is by using the token!
        assert len(session.query(Agent).all()) == initial_agent_count

    def test_cannot_create_agent_with_invalid_type(self, test_client):
        raw_agent = self.create_raw_agent(_type="wrong_type")
        res = test_client.post(self.url(), data=raw_agent)
        assert res.status_code == 405  # the only way to create agents is by using the token!

    def test_cannot_create_agent_with_invalid_status(self, test_client):
        raw_agent = self.create_raw_agent(status="wrong_status")
        res = test_client.post(self.url(), data=raw_agent)
        assert res.status_code == 405  # you can only create agents by using the token

    def test_update_agent(self, test_client, session):
        agent = AgentFactory.create(workspace=self.workspace, type='shared')
        session.commit()
        raw_agent = self.create_raw_agent(_type="specific")
        res = test_client.put(self.url(agent.id), data=raw_agent)
        assert res.status_code == 200
        assert res.json['type'] == 'specific'

    def test_delete_agent(self, test_client, session):
        initial_agent_count = len(session.query(Agent).all())
        agent = AgentFactory.create(workspace=self.workspace, type='shared')
        session.commit()
        assert len(session.query(Agent).all()) == initial_agent_count + 1
        res = test_client.delete(self.url(agent.id))
        assert res.status_code == 204
        assert len(session.query(Agent).all()) == initial_agent_count
