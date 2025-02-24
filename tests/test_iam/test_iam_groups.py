from datetime import datetime

import boto3
import sure  # noqa  # pylint: disable=unused-import
import json

import pytest
from botocore.exceptions import ClientError
from moto import mock_iam, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.backends import get_backend
from freezegun import freeze_time
from dateutil.tz import tzlocal

MOCK_POLICY = """
{
  "Version": "2012-10-17",
  "Statement":
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example_bucket"
    }
}
"""


@mock_iam
def test_create_group():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    with pytest.raises(ClientError) as ex:
        conn.create_group(GroupName="my-group")
    err = ex.value.response["Error"]
    err["Code"].should.equal("Group my-group already exists")
    err["Message"].should.equal(None)


@mock_iam
def test_get_group():
    conn = boto3.client("iam", region_name="us-east-1")
    created = conn.create_group(GroupName="my-group")["Group"]
    created["Path"].should.equal("/")
    created["GroupName"].should.equal("my-group")
    created.should.have.key("GroupId")
    created["Arn"].should.equal(f"arn:aws:iam::{ACCOUNT_ID}:group/my-group")
    created["CreateDate"].should.be.a(datetime)

    retrieved = conn.get_group(GroupName="my-group")["Group"]
    retrieved.should.equal(created)

    with pytest.raises(ClientError) as ex:
        conn.get_group(GroupName="not-group")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal("Group not-group not found")


@mock_iam()
def test_get_group_current():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    result = conn.get_group(GroupName="my-group")

    assert result["Group"]["Path"] == "/"
    assert result["Group"]["GroupName"] == "my-group"
    assert isinstance(result["Group"]["CreateDate"], datetime)
    assert result["Group"]["GroupId"]
    assert result["Group"]["Arn"] == f"arn:aws:iam::{ACCOUNT_ID}:group/my-group"
    assert not result["Users"]

    # Make a group with a different path:
    other_group = conn.create_group(GroupName="my-other-group", Path="/some/location/")
    assert other_group["Group"]["Path"] == "/some/location/"
    assert (
        other_group["Group"]["Arn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:group/some/location/my-other-group"
    )


@mock_iam
def test_get_all_groups():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group1")
    conn.create_group(GroupName="my-group2")
    groups = conn.list_groups()["Groups"]
    groups.should.have.length_of(2)


@mock_iam
def test_add_unknown_user_to_group():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        conn.add_user_to_group(GroupName="my-group", UserName="my-user")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal("The user with name my-user cannot be found.")


@mock_iam
def test_add_user_to_unknown_group():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    with pytest.raises(ClientError) as ex:
        conn.add_user_to_group(GroupName="my-group", UserName="my-user")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal("Group my-group not found")


@mock_iam
def test_add_user_to_group():
    # Setup
    frozen_time = datetime(2023, 5, 20, 10, 20, 30, tzinfo=tzlocal())

    group = "my-group"
    user = "my-user"
    with freeze_time(frozen_time):
        conn = boto3.client("iam", region_name="us-east-1")
        conn.create_group(GroupName=group)
        conn.create_user(UserName=user)
        conn.add_user_to_group(GroupName=group, UserName=user)

        # use internal api to set password, doesn't work in servermode
        if not settings.TEST_SERVER_MODE:
            iam_backend = get_backend("iam")[ACCOUNT_ID]["global"]
            iam_backend.users[user].password_last_used = datetime.utcnow()
    # Execute
    result = conn.get_group(GroupName=group)

    # Verify
    assert len(result["Users"]) == 1

    # if in servermode then we can't test for password because we can't
    # manipulate the backend with internal an api
    if settings.TEST_SERVER_MODE:
        assert "CreateDate" in result["Users"][0]
        return
    assert result["Users"][0]["CreateDate"] == frozen_time
    assert result["Users"][0]["PasswordLastUsed"] == frozen_time


@mock_iam
def test_remove_user_from_unknown_group():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        conn.remove_user_from_group(GroupName="my-group", UserName="my-user")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal("Group my-group not found")


@mock_iam
def test_remove_nonattached_user_from_group():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    conn.create_user(UserName="my-user")
    with pytest.raises(ClientError) as ex:
        conn.remove_user_from_group(GroupName="my-group", UserName="my-user")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal("User my-user not in group my-group")


@mock_iam
def test_remove_user_from_group():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    conn.create_user(UserName="my-user")
    conn.add_user_to_group(GroupName="my-group", UserName="my-user")
    conn.remove_user_from_group(GroupName="my-group", UserName="my-user")


@mock_iam
def test_add_user_should_be_idempotent():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    conn.create_user(UserName="my-user")
    # We'll add the same user twice, but it should only be persisted once
    conn.add_user_to_group(GroupName="my-group", UserName="my-user")
    conn.add_user_to_group(GroupName="my-group", UserName="my-user")

    conn.list_groups_for_user(UserName="my-user")["Groups"].should.have.length_of(1)

    # Which means that if we remove one, none should be left
    conn.remove_user_from_group(GroupName="my-group", UserName="my-user")

    conn.list_groups_for_user(UserName="my-user")["Groups"].should.have.length_of(0)


@mock_iam
def test_get_groups_for_user():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group1")
    conn.create_group(GroupName="my-group2")
    conn.create_group(GroupName="other-group")
    conn.create_user(UserName="my-user")
    conn.add_user_to_group(GroupName="my-group1", UserName="my-user")
    conn.add_user_to_group(GroupName="my-group2", UserName="my-user")

    groups = conn.list_groups_for_user(UserName="my-user")["Groups"]
    groups.should.have.length_of(2)


@mock_iam
def test_put_group_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    conn.put_group_policy(
        GroupName="my-group", PolicyName="my-policy", PolicyDocument=MOCK_POLICY
    )


@mock_iam
def test_attach_group_policies():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    conn.list_attached_group_policies(GroupName="my-group")[
        "AttachedPolicies"
    ].should.be.empty
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
    conn.list_attached_group_policies(GroupName="my-group")[
        "AttachedPolicies"
    ].should.be.empty
    conn.attach_group_policy(GroupName="my-group", PolicyArn=policy_arn)
    conn.list_attached_group_policies(GroupName="my-group")[
        "AttachedPolicies"
    ].should.equal(
        [{"PolicyName": "AmazonElasticMapReduceforEC2Role", "PolicyArn": policy_arn}]
    )

    conn.detach_group_policy(GroupName="my-group", PolicyArn=policy_arn)
    conn.list_attached_group_policies(GroupName="my-group")[
        "AttachedPolicies"
    ].should.be.empty


@mock_iam
def test_get_group_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    with pytest.raises(ClientError) as ex:
        conn.get_group_policy(GroupName="my-group", PolicyName="my-policy")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal("Policy my-policy not found")

    conn.put_group_policy(
        GroupName="my-group", PolicyName="my-policy", PolicyDocument=MOCK_POLICY
    )
    policy = conn.get_group_policy(GroupName="my-group", PolicyName="my-policy")
    policy["GroupName"].should.equal("my-group")
    policy["PolicyName"].should.equal("my-policy")
    policy["PolicyDocument"].should.equal(json.loads(MOCK_POLICY))


@mock_iam()
def test_list_group_policies():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    conn.list_group_policies(GroupName="my-group")["PolicyNames"].should.be.empty
    conn.put_group_policy(
        GroupName="my-group", PolicyName="my-policy", PolicyDocument=MOCK_POLICY
    )
    conn.list_group_policies(GroupName="my-group")["PolicyNames"].should.equal(
        ["my-policy"]
    )


@mock_iam
def test_delete_group():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    groups = conn.list_groups()
    assert groups["Groups"][0]["GroupName"] == "my-group"
    assert len(groups["Groups"]) == 1
    conn.delete_group(GroupName="my-group")
    conn.list_groups()["Groups"].should.be.empty


@mock_iam
def test_delete_unknown_group():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as err:
        conn.delete_group(GroupName="unknown-group")
    err.value.response["Error"]["Code"].should.equal("NoSuchEntity")
    err.value.response["Error"]["Message"].should.equal(
        "The group with name unknown-group cannot be found."
    )


@mock_iam
def test_update_group_name():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    initial_group = conn.get_group(GroupName="my-group")["Group"]

    conn.update_group(GroupName="my-group", NewGroupName="new-group")

    # The old group-name should no longer exist
    with pytest.raises(ClientError) as exc:
        conn.get_group(GroupName="my-group")
    exc.value.response["Error"]["Code"].should.equal("NoSuchEntity")

    result = conn.get_group(GroupName="new-group")["Group"]
    result["Path"].should.equal("/")
    result["GroupName"].should.equal("new-group")
    result["GroupId"].should.equal(initial_group["GroupId"])
    result["Arn"].should.match(":group/new-group")


@mock_iam
def test_update_group_name_that_has_a_path():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group", Path="/path")

    conn.update_group(GroupName="my-group", NewGroupName="new-group")

    # Verify the path hasn't changed
    new = conn.get_group(GroupName="new-group")["Group"]
    new["Path"].should.equal("/path")


@mock_iam
def test_update_group_path():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group", Path="/path")

    conn.update_group(
        GroupName="my-group", NewGroupName="new-group", NewPath="/new-path"
    )

    # Verify the path has changed
    new = conn.get_group(GroupName="new-group")["Group"]
    new["Path"].should.equal("/new-path")


@mock_iam
def test_update_group_that_does_not_exist():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        conn.update_group(GroupName="nonexisting", NewGroupName="..")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal("The group with name nonexisting cannot be found.")


@mock_iam
def test_update_group_with_existing_name():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="existing1")
    conn.create_group(GroupName="existing2")

    with pytest.raises(ClientError) as exc:
        conn.update_group(GroupName="existing1", NewGroupName="existing2")
    err = exc.value.response["Error"]
    err["Code"].should.equal("Conflict")
    err["Message"].should.equal("Group existing2 already exists")
