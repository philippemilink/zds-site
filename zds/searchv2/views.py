from zds import json_handler

from datetime import datetime

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic.detail import SingleObjectMixin

from zds.searchv2.forms import SearchForm
from zds.searchv2.models import SearchIndexManager
from zds.utils.paginator import ZdSPagingListView
from zds.utils.templatetags.authorized_forums import get_authorized_forums

from .client import client


class SimilarTopicsView(CreateView, SingleObjectMixin):
    """
    This view allows you to suggest similar topics when creating a new topic on a forum.
    The idea is to avoid the creation of a topic on a subject already treated on the forum.
    """

    search_query = None
    authorized_forums = ""
    search_engine_manager = None

    def __init__(self, **kwargs):
        """Overridden because the index manager must NOT be initialized elsewhere."""
        super().__init__(**kwargs)
        self.search_engine_manager = SearchIndexManager()

    def get(self, request, *args, **kwargs):
        if "q" in request.GET:
            self.search_query = "".join(request.GET["q"])

        results = []
        if self.search_engine_manager.connected_to_search_engine and self.search_query:
            self.authorized_forums = get_authorized_forums(self.request.user)
            filter = self._add_numerical_filter("forum_pk", self.authorized_forums)
            search_parameters = {
                "q": self.search_query,
                "query_by": "title,subtitle,tags",
                "filter_by": filter,
            }

            result = client.collections["topic"].documents.search(search_parameters)["hits"]

            for entry in result:
                entry["collection"] = "topic"

            hits = client.collections["topic"].documents.search(search_parameters)["hits"][:10]

            # Build the result
            for hit in hits:
                document = hit["document"]["_source"]
                result = {
                    "id": document["id"],
                    "url": str(document["get_absolute_url"]),
                    "title": str(document["title"]),
                    "subtitle": str(document["subtitle"]),
                    "forumTitle": str(document["forum_title"]),
                    "forumUrl": str(document["forum_get_absolute_url"]),
                    "pubdate": str(datetime.fromtimestamp(document["pubdate"])),
                }
                results.append(result)

        data = {"results": results}
        return HttpResponse(json_handler.dumps(data), content_type="application/json")

    def _add_numerical_filter(self, field, values):
        """
        Return a filter (string), this filter is used for numerical values necessary for the field
        field : it's a string with the name of the field to filter
        values : is a list of int with value that we want for the field
        """
        filter = f"{field}:={values[0]}"
        for value in values[1:]:
            filter += f"||{field}:={value}"
        return filter


class SuggestionContentView(CreateView, SingleObjectMixin):
    """
    Staff members can choose at the end of a publication to suggest another content of the site. can choose at the end of a publication to suggest another content of the site.
    When they want to add a suggestion, they write in a text field the name of the content to suggest,
    content proposals are then made, using the search engine through this view.
    """

    search_query = None
    authorized_forums = ""
    search_engine_manager = None

    def __init__(self, **kwargs):
        """Overridden because the index manager must NOT be initialized elsewhere."""

        super().__init__(**kwargs)
        self.search_engine_manager = SearchIndexManager()

    def get(self, request, *args, **kwargs):
        if "q" in request.GET:
            self.search_query = "".join(request.GET["q"])
        excluded_content_ids = request.GET.get("excluded", "").split(",")
        results = []
        if self.search_engine_manager.connected_to_search_engine and self.search_query:
            self.authorized_forums = get_authorized_forums(self.request.user)

            search_parameters = {
                "q": self.search_query,
                "query_by": "title,description",
            }

            if len(excluded_content_ids) > 0 and excluded_content_ids != [""]:
                search_parameters["filter_by"] = self._add_negative_numerical_filter("content_pk", excluded_content_ids)

            hits = client.collections["publishedcontent"].documents.search(search_parameters)["hits"][:10]

            # Build the result
            for hit in hits:
                document = hit["document"]["_source"]
                result = {
                    "id": document["content_pk"],
                    "pubdate": document["publication_date"],
                    "title": str(document["title"]),
                    "description": str(document["description"]),
                }
                results.append(result)
        data = {"results": results}

        return HttpResponse(json_handler.dumps(data), content_type="application/json")

    def _add_negative_numerical_filter(self, field, values):
        """
        Add a filter to the current filter, this filter is used for numerical negation
        Indeed, in 0.24.0, Typesense doesn't allow excluding a numerical value
        field : it's a string with the name of the field to filter
        values : is a list of strings with value that we don't want for the field
        """
        filter = f"({field}:<{values[0]}||{field}:>{values[0]})"
        for value in values[1:]:
            filter += f"&&({field}:<{value}||{field}:>{value})"
        return filter


class SearchView(ZdSPagingListView):
    """Search view."""

    template_name = "searchv2/search.html"
    paginate_by = settings.ZDS_APP["search"]["results_per_page"]

    search_form_class = SearchForm
    search_form = None
    search_query = None
    content_category = None
    content_subcategory = None
    search_content_types = None
    search_content_types_count = None
    search_validated_content = None

    authorized_forums = ""

    search_engine_manager = None

    def __init__(self, **kwargs):
        """Overridden because the index manager must NOT be initialized elsewhere."""

        super().__init__(**kwargs)
        self.search_engine_manager = SearchIndexManager()

    def get(self, request, *args, **kwargs):
        """Overridden to catch the request and fill the form."""

        if "q" in request.GET:
            self.search_query = "".join(request.GET["q"])

        self.authorized_forums = get_authorized_forums(self.request.user)

        self.search_form = self.search_form_class(data=self.request.GET)

        if self.search_query and not self.search_form.is_valid():
            raise PermissionDenied("research form is invalid")

        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if not self.search_engine_manager.connected_to_search_engine:
            messages.warning(self.request, _("Impossible de se connecter à Elasticsearch"))
            return []

        if self.search_query:
            # Restrict (sub)category if any
            if self.search_form.cleaned_data["category"]:
                self.content_category = self.search_form.cleaned_data["category"]
            if self.search_form.cleaned_data["subcategory"]:
                self.content_subcategory = self.search_form.cleaned_data["subcategory"]

            # Mark that contents must come from library if required
            self.from_library = False
            if self.search_form.cleaned_data["from_library"] == "on":
                self.from_library = True

            # Check in which collections search is performed
            search_collections = self.search_form.cleaned_data["models"]
            search_collection_count = len(search_collections)
            if search_collection_count == 0:
                search_collections = ["publishedcontent", "topic", "chapter", "post"]

            # Check which content types are searched
            self.search_content_types = self.search_form.cleaned_data["content_types"]
            self.search_content_types_count = len(self.search_content_types)

            # Check if the content must be validated
            self.search_validated_content = self.search_form.cleaned_data["validated_content"]

            # Check if the forum is authori
            filter = ""
            filter = self._add_filter("forum_pk", self.authorized_forums, filter)

            search_requests = {"searches": []}

            searches = {
                "publishedcontent": {
                    "collection": "publishedcontent",
                    "q": self.search_query,
                    "query_by": "title,description,categories,subcategories, tags, text",
                    "query_by_weights": f"{settings.ZDS_APP['search']['boosts']['publishedcontent']['title']},{settings.ZDS_APP['search']['boosts']['publishedcontent']['description']},{settings.ZDS_APP['search']['boosts']['publishedcontent']['categories']},{settings.ZDS_APP['search']['boosts']['publishedcontent']['subcategories']},{settings.ZDS_APP['search']['boosts']['publishedcontent']['tags']},{settings.ZDS_APP['search']['boosts']['publishedcontent']['text']}",
                },
                "topic": {
                    "collection": "topic",
                    "q": self.search_query,
                    "query_by": "title,subtitle,tags",
                    "filter_by": filter,
                    "query_by_weights": f"{settings.ZDS_APP['search']['boosts']['topic']['title']},{settings.ZDS_APP['search']['boosts']['topic']['subtitle']},{settings.ZDS_APP['search']['boosts']['topic']['tags']}",
                },
                "chapter": {
                    "collection": "chapter",
                    "q": self.search_query,
                    "query_by": "title,text",
                    "query_by_weights": f"{settings.ZDS_APP['search']['boosts']['chapter']['title']},{settings.ZDS_APP['search']['boosts']['chapter']['text']}",
                },
                "post": {
                    "collection": "post",
                    "q": self.search_query,
                    "query_by": "text_html",
                    "filter_by": filter,
                    "query_by_weights": f"{settings.ZDS_APP['search']['boosts']['post']['text_html']}",
                },
            }
            if self.search_content_types:
                searches["publishedcontent"]["filter"] = self._add_filter("content_type", self.search_content_types, "")
                search_collections = ["publishedcontent"]
                search_collection_count = 1

            if self.search_validated_content:
                search_collections = ["publishedcontent"]
                search_collection_count = 1
                if len(self.search_validated_content) == 1:
                    if self.search_validated_content[0] == "validated":
                        self.search_content_types = ["tutorial", "article"]
                        self.search_content_types_count = 2
                    else:
                        self.search_content_types = "opinion"
                        self.search_content_types_count = 1
            result = None
            if search_collection_count == 1:
                result = self._choose_single_collection_method(search_collections[0])
            else:
                for name in search_collections:
                    search_requests["searches"].append(searches[name])
                result = self.get_queryset_multisearch(search_requests, search_collections)
            return result
        return []

    def get_queryset_multisearch(self, search_requests, collection_names):
        """Return search in several collections
        @search_requests : parameters of search
        @collection_names : name of the collection to search
        """
        results = client.multi_search.perform(search_requests, None)["results"]
        all_collection_result = []
        for k in range(len(results)):
            if "hits" in results[k]:
                for entry in results[k]["hits"]:
                    entry["collection"] = collection_names[k]
                    all_collection_result.append(entry)
        all_collection_result.sort(key=lambda result: result["text_match"], reverse=True)
        count_results = len(all_collection_result)
        if count_results > 10:
            for i in range(int(count_results / 10)):
                print(all_collection_result[i * 10 : (i + 1) * 10])
                all_collection_result[i * 10 : (i + 1) * 10] = sorted(
                    all_collection_result[i * 10 : (i + 1) * 10],
                    key=lambda result: result["document"]["score"],
                    reverse=True,
                )
                print(all_collection_result[i * 10 : (i + 1) * 10])

        return all_collection_result

    def get_queryset_publishedcontents(self):
        """Search in PublishedContent collection."""
        filter = ""
        if self.search_content_types:
            filter = self._add_filter("content_type", self.search_content_types, filter)

        if self.content_category:
            filter = self._add_filter("categories", self.content_category, filter)

        if self.content_subcategory:
            filter = self._add_filter("subcategories", self.content_subcategory, filter)

        search_parameters = {
            "q": self.search_query,
            "query_by": "title,description,categories,subcategories, tags, text",
            "filter_by": filter,
            "sort_by": "score:desc",
        }

        result = client.collections["publishedcontent"].documents.search(search_parameters)["hits"]

        for entry in result:
            entry["collection"] = "publishedcontent"

        return result

    def get_queryset_chapters(self):
        """Search in chapters collection."""
        filter = ""
        if self.content_category:
            filter = self._add_filter("categories", self.content_category, filter)

        if self.content_subcategory:
            filter = self._add_filter("subcategories", self.content_subcategory, filter)

        search_parameters = {
            "q": self.search_query,
            "query_by": "title,text",
            "filter": filter,
            "sort_by": "score:desc",
        }

        result = client.collections["chapter"].documents.search(search_parameters)["hits"]

        for entry in result:
            entry["collection"] = "chapter"

        return result

    def get_queryset_topics(self):
        """Search in topics, and remove the result if the forum is not allowed for the user.

        Score is modified if:

        + topic is solved;
        + topic is sticky;
        + topic is locked.
        """
        filter = ""
        filter = self._add_filter("forum_pk", self.authorized_forums, filter)

        search_parameters = {
            "q": self.search_query,
            "query_by": "title,subtitle,tags",
            "filter_by": filter,
            "sort_by": "score:desc",
        }

        result = client.collections["topic"].documents.search(search_parameters)["hits"]

        for entry in result:
            entry["collection"] = "topic"

        return result

    def get_queryset_posts(self):
        """Search in posts, and remove result if the forum is not allowed for the user or if the message is invisible.

        Score is modified if:

        + post is the first one in a topic;
        + post is marked as "useful";
        + post has a like/dislike ratio above (has more likes than dislikes) or below (the other way around) 1.0.
        """

        filter = ""
        filter = self._add_filter("forum_pk", self.authorized_forums, filter)
        filter = self._add_filter("is_visible", "true", filter)
        search_parameters = {
            "q": self.search_query,
            "query_by": "text_html",
            "filter_by": filter,
            "sort_by": "score:desc",
        }

        result = client.collections["post"].documents.search(search_parameters)["hits"]

        for entry in result:
            entry["collection"] = "post"

        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.search_form
        context["query"] = self.search_query is not None
        return context

    def _add_filter(self, field, value, current_filter):
        """
        Add a filter to the current filter, this filter can't be used for negation
        field : it's a string with the name of the field to filter
        value : is the a string with value of the field
        current_filter : is the current string which represents the value to filter
        """
        if len(current_filter) > 0:
            current_filter += f"&& {field}:{str(value)}"
        else:
            current_filter = f"{field}:{str(value)}"
        return current_filter

    def _choose_single_collection_method(self, name):
        """
        Return the result of search according the @name of the collection
        """
        if name == "publishedcontent":
            return self.get_queryset_publishedcontents()
        elif name == "post":
            return self.get_queryset_posts()
        elif name == "topic":
            return self.get_queryset_topics()
        else:
            raise "Unknown collection name"


def opensearch(request):
    """Generate OpenSearch Description file."""

    return render(
        request,
        "searchv2/opensearch.xml",
        {
            "site_name": settings.ZDS_APP["site"]["literal_name"],
            "site_url": settings.ZDS_APP["site"]["url"],
            "email_contact": settings.ZDS_APP["site"]["email_contact"],
            "language": settings.LANGUAGE_CODE,
            "search_url": settings.ZDS_APP["site"]["url"] + reverse("search:query"),
        },
        content_type="application/opensearchdescription+xml",
    )
