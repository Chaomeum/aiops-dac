"""Installed diagrams icons selected only from confirmed model facts."""

import inspect

from diagrams import Node
from diagrams.azure.compute import ContainerApps
from diagrams.azure.identity import ActiveDirectory
from diagrams.azure.integration import APIManagement, ServiceBus
from diagrams.azure.ml import AzureOpenAI
from diagrams.azure.monitor import Monitor
from diagrams.azure.storage import BlobStorage
from diagrams.azure.web import StaticApps
from diagrams.generic.blank import Blank
from diagrams.onprem.client import Users
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.vcs import Github

TECHNOLOGY_ICONS = {
    "Azure API Management": APIManagement,
    # The installed package retains the former Azure AD name for Entra ID.
    "Microsoft Entra ID": ActiveDirectory,
    "Azure Service Bus": ServiceBus,
    "PostgreSQL": PostgreSQL,
    "Azure Monitor": Monitor,
    "Azure Blob Storage": BlobStorage,
}
HOST_ICONS = {
    "Azure Container Apps": ContainerApps,
    "Azure Static Web Apps": StaticApps,
}
EXTERNAL_ICONS = {"GitHub": Github, "GitHub Actions": GithubActions}

for _icon in {*TECHNOLOGY_ICONS.values(), *HOST_ICONS.values(),
              *EXTERNAL_ICONS.values(), APIManagement, AzureOpenAI, Users, Blank}:
    if not inspect.isclass(_icon) or not issubclass(_icon, Node):
        raise RuntimeError(f"Invalid installed diagrams icon: {_icon}")


def icon_for(element):
    """Return a specific icon, or None when a neutral fallback is needed.

    Hosting icons describe the host, not the component's implementation.
    In particular, Container Apps never confirms the LogBERT candidate.
    """
    if element.get("status") != "confirmed":
        return None
    technology = element.get("technology") or {}
    if technology.get("decision_status") == "closed":
        icon = TECHNOLOGY_ICONS.get(technology.get("name"))
        if icon:
            return icon
        if technology.get("name") == "pgvector" and element.get("parent_technology") == "PostgreSQL":
            return PostgreSQL
        if technology.get("api_perimeter") == "Azure API Management":
            return APIManagement
    icon = HOST_ICONS.get((element.get("host") or {}).get("concrete_service"))
    if icon:
        return icon
    if (element.get("provider") == "Azure OpenAI Service"
            and (element.get("deployment_mode") or {}).get("decision_status") == "closed"):
        return AzureOpenAI
    if element.get("kind") == "external_system":
        return EXTERNAL_ICONS.get(element.get("name"))
    if element.get("kind") == "actor":
        return Users
    return None


def fallback_icon_for(element):
    """A blank package icon adds no technology decision to the model."""
    return Blank
