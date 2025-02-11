import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_create_authorizer_minimum():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_authorizer(
        ApiId=api_id,
        AuthorizerType="REQUEST",
        IdentitySource=[],
        Name="auth1",
        AuthorizerPayloadFormatVersion="2.0",
    )

    assert "AuthorizerId" in resp
    assert resp["AuthorizerType"] == "REQUEST"
    assert resp["Name"] == "auth1"


@mock_apigatewayv2
def test_create_authorizer():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.create_authorizer(
        ApiId=api_id,
        AuthorizerCredentialsArn="auth:creds:arn",
        AuthorizerPayloadFormatVersion="2.0",
        AuthorizerResultTtlInSeconds=3,
        AuthorizerType="REQUEST",
        AuthorizerUri="auth_uri",
        EnableSimpleResponses=True,
        IdentitySource=["$request.header.Authorization"],
        IdentityValidationExpression="ive",
        JwtConfiguration={"Audience": ["a1"], "Issuer": "moto.com"},
        Name="auth1",
    )

    assert "AuthorizerId" in resp
    assert resp["AuthorizerCredentialsArn"] == "auth:creds:arn"
    assert resp["AuthorizerPayloadFormatVersion"] == "2.0"
    assert resp["AuthorizerResultTtlInSeconds"] == 3
    assert resp["AuthorizerType"] == "REQUEST"
    assert resp["AuthorizerUri"] == "auth_uri"
    assert resp["EnableSimpleResponses"] is True
    assert resp["IdentitySource"] == ["$request.header.Authorization"]
    assert resp["IdentityValidationExpression"] == "ive"
    assert resp["JwtConfiguration"] == {"Audience": ["a1"], "Issuer": "moto.com"}
    assert resp["Name"] == "auth1"
    assert resp["AuthorizerPayloadFormatVersion"] == "2.0"


@mock_apigatewayv2
def test_create_authorizer_without_payloadformatversion():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    with pytest.raises(ClientError) as exc:
        client.create_authorizer(
            ApiId=api_id,
            AuthorizerType="REQUEST",
            AuthorizerUri="auth_uri",
            IdentitySource=[""],
            Name="auth1",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert (
        err["Message"]
        == "AuthorizerPayloadFormatVersion is a required parameter for REQUEST authorizer"
    )


@mock_apigatewayv2
def test_get_authorizer():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    authorizer_id = client.create_authorizer(
        ApiId=api_id,
        AuthorizerType="REQUEST",
        IdentitySource=[],
        Name="auth1",
        AuthorizerPayloadFormatVersion="2.0",
    )["AuthorizerId"]

    resp = client.get_authorizer(ApiId=api_id, AuthorizerId=authorizer_id)

    assert "AuthorizerId" in resp
    assert resp["AuthorizerType"] == "REQUEST"
    assert resp["Name"] == "auth1"
    assert resp["AuthorizerPayloadFormatVersion"] == "2.0"


@mock_apigatewayv2
def test_delete_authorizer():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="WEBSOCKET")["ApiId"]

    authorizer_id = client.create_authorizer(
        ApiId=api_id, AuthorizerType="REQUEST", IdentitySource=[], Name="auth1"
    )["AuthorizerId"]

    client.delete_authorizer(ApiId=api_id, AuthorizerId=authorizer_id)

    with pytest.raises(ClientError) as exc:
        client.get_authorizer(ApiId=api_id, AuthorizerId="unknown")

    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"


@mock_apigatewayv2
def test_get_authorizer_unknown():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    with pytest.raises(ClientError) as exc:
        client.get_authorizer(ApiId=api_id, AuthorizerId="unknown")

    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"


@mock_apigatewayv2
def test_update_authorizer_single():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    auth_id = client.create_authorizer(
        ApiId=api_id,
        AuthorizerCredentialsArn="auth:creds:arn",
        AuthorizerPayloadFormatVersion="2.0",
        AuthorizerResultTtlInSeconds=3,
        AuthorizerType="REQUEST",
        AuthorizerUri="auth_uri",
        EnableSimpleResponses=True,
        IdentitySource=["$request.header.Authorization"],
        IdentityValidationExpression="ive",
        JwtConfiguration={"Audience": ["a1"], "Issuer": "moto.com"},
        Name="auth1",
    )["AuthorizerId"]

    resp = client.update_authorizer(ApiId=api_id, AuthorizerId=auth_id, Name="auth2")

    assert "AuthorizerId" in resp
    assert resp["AuthorizerCredentialsArn"] == "auth:creds:arn"
    assert resp["AuthorizerPayloadFormatVersion"] == "2.0"
    assert resp["AuthorizerResultTtlInSeconds"] == 3
    assert resp["AuthorizerType"] == "REQUEST"
    assert resp["AuthorizerUri"] == "auth_uri"
    assert resp["EnableSimpleResponses"] is True
    assert resp["IdentitySource"] == ["$request.header.Authorization"]
    assert resp["IdentityValidationExpression"] == "ive"
    assert resp["JwtConfiguration"] == {"Audience": ["a1"], "Issuer": "moto.com"}
    assert resp["Name"] == "auth2"


@mock_apigatewayv2
def test_update_authorizer_all_attributes():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    auth_id = client.create_authorizer(
        ApiId=api_id,
        AuthorizerType="REQUEST",
        IdentitySource=[],
        Name="auth1",
        AuthorizerPayloadFormatVersion="2.0",
    )["AuthorizerId"]

    auth_id = client.update_authorizer(
        ApiId=api_id,
        AuthorizerId=auth_id,
        AuthorizerCredentialsArn="",
        AuthorizerPayloadFormatVersion="3.0",
        AuthorizerResultTtlInSeconds=5,
        AuthorizerType="REQUEST",
        AuthorizerUri="auth_uri",
        EnableSimpleResponses=False,
        IdentitySource=["$request.header.Authentication"],
        IdentityValidationExpression="ive2",
        JwtConfiguration={"Audience": ["a2"], "Issuer": "moto.com"},
        Name="auth1",
    )["AuthorizerId"]

    resp = client.update_authorizer(ApiId=api_id, AuthorizerId=auth_id, Name="auth2")

    assert "AuthorizerId" in resp
    assert resp["AuthorizerCredentialsArn"] == ""
    assert resp["AuthorizerPayloadFormatVersion"] == "3.0"
    assert resp["AuthorizerResultTtlInSeconds"] == 5
    assert resp["AuthorizerType"] == "REQUEST"
    assert resp["AuthorizerUri"] == "auth_uri"
    assert resp["EnableSimpleResponses"] is False
    assert resp["IdentitySource"] == ["$request.header.Authentication"]
    assert resp["IdentityValidationExpression"] == "ive2"
    assert resp["JwtConfiguration"] == {"Audience": ["a2"], "Issuer": "moto.com"}
    assert resp["Name"] == "auth2"
