from django.conf import settings
from django.test import TestCase
from django.core.management import call_command

from zds.member.tests.factories import ProfileFactory, StaffProfileFactory
from zds.tutorialv2.tests.factories import PublishableContentFactory, ContainerFactory, ExtractFactory
from zds.tutorialv2.models.database import PublishedContent
from zds.tutorialv2.publication_utils import publish_content
from zds.forum.tests.factories import TopicFactory, PostFactory, Topic, Post
from zds.forum.tests.factories import create_category_and_forum
from zds.searchv2.models import SearchIndexManager
from zds.tutorialv2.tests import TutorialTestMixin, override_for_contents


@override_for_contents(SEARCH_ENABLED=True)
class UtilsTests(TutorialTestMixin, TestCase):
    def setUp(self):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        self.mas = ProfileFactory().user
        settings.ZDS_APP["member"]["bot_account"] = self.mas.username

        self.category, self.forum = create_category_and_forum()

        self.user = ProfileFactory().user
        self.staff = StaffProfileFactory().user

        self.search_engine_manager = SearchIndexManager()

    def test_manager(self):
        """Test the behavior of the ``search_engine_manager`` command"""

        if not self.search_engine_manager.connected_to_search_engine:
            return

        # in the beginning: the void
        self.assertTrue(len(self.search_engine_manager.search_engine.collections.retrieve()) == 0)

        text = "Ceci est un texte de test"

        # create a topic with a post
        topic = TopicFactory(forum=self.forum, author=self.user, title=text)
        post = PostFactory(topic=topic, author=self.user, position=1)
        post.text = post.text_html = text
        post.save()

        topic = Topic.objects.get(pk=topic.pk)
        post = Post.objects.get(pk=post.pk)

        self.assertFalse(topic.search_engine_already_indexed)
        self.assertTrue(topic.search_engine_flagged)
        self.assertFalse(post.search_engine_already_indexed)
        self.assertTrue(post.search_engine_flagged)

        # create a middle-tutorial and publish it
        tuto = PublishableContentFactory(type="TUTORIAL")
        tuto.authors.add(self.user)
        tuto.save()

        tuto_draft = tuto.load_version()
        chapter1 = ContainerFactory(parent=tuto_draft, db_object=tuto)
        chapter1.repo_update(text, text, text)
        extract1 = ExtractFactory(container=chapter1, db_object=tuto)
        version = extract1.repo_update(text, text)
        published = publish_content(tuto, tuto_draft, is_major_update=True)

        tuto.sha_public = version
        tuto.sha_draft = version
        tuto.public_version = published
        tuto.save()

        published = PublishedContent.objects.get(content_pk=tuto.pk)
        self.assertFalse(published.search_engine_already_indexed)
        self.assertTrue(published.search_engine_flagged)

        # 1. test "index-all"
        call_command("search_engine_manager", "index_all")
        self.assertTrue(len(self.search_engine_manager.search_engine.collections.retrieve()) != 0)

        topic = Topic.objects.get(pk=topic.pk)
        post = Post.objects.get(pk=post.pk)

        self.assertTrue(topic.search_engine_already_indexed)
        self.assertFalse(topic.search_engine_flagged)
        self.assertTrue(post.search_engine_already_indexed)
        self.assertFalse(post.search_engine_flagged)

        published = PublishedContent.objects.get(content_pk=tuto.pk)
        self.assertTrue(published.search_engine_already_indexed)
        self.assertFalse(published.search_engine_flagged)

        results = self.search_engine_manager.setup_search("*")
        number_of_results = sum(result["found"] for result in results)
        self.assertEqual(number_of_results, 4)  # get 4 results, one of each type

        must_contain = {"post": False, "topic": False, "publishedcontent": False, "chapter": False}
        id_must_be = {
            "post": str(post.pk),
            "topic": str(topic.pk),
            "publishedcontent": str(published.pk),
            "chapter": tuto.slug + "__" + chapter1.slug,
        }

        for result in results:
            doc_type = result["request_params"]["collection_name"]
            must_contain[doc_type] = True
            for hit in result["hits"]:
                doc_id = hit["document"]["id"]
                self.assertEqual(doc_id, id_must_be[doc_type])

        self.assertTrue(all(must_contain))

        # 2. test "clear"
        self.assertTrue(len(self.search_engine_manager.search_engine.collections.retrieve()) != 0)

        call_command("search_engine_manager", "clear")
        self.assertTrue(len(self.search_engine_manager.search_engine.collections.retrieve()) == 0)  # back to void

        # must reset every object
        topic = Topic.objects.get(pk=topic.pk)
        post = Post.objects.get(pk=post.pk)

        self.assertFalse(topic.search_engine_already_indexed)
        self.assertTrue(topic.search_engine_flagged)
        self.assertFalse(post.search_engine_already_indexed)
        self.assertTrue(post.search_engine_flagged)

        published = PublishedContent.objects.get(content_pk=tuto.pk)
        self.assertFalse(published.search_engine_already_indexed)
        self.assertTrue(published.search_engine_flagged)

        # 3. test "setup"
        print(self.search_engine_manager.search_engine.collections.retrieve())
        call_command("search_engine_manager", "setup")

        self.assertTrue(
            len(self.search_engine_manager.search_engine.collections.retrieve()) != 0
        )  # collections back in

        results = self.search_engine_manager.setup_search("*")
        number_of_results = sum(result["found"] for result in results)
        self.assertEqual(number_of_results, 0)  # ... but with nothing in it

        # 4. test "index-flagged" once ...
        call_command("search_engine_manager", "index_flagged")

        topic = Topic.objects.get(pk=topic.pk)
        post = Post.objects.get(pk=post.pk)

        self.assertTrue(topic.search_engine_already_indexed)
        self.assertFalse(topic.search_engine_flagged)
        self.assertTrue(post.search_engine_already_indexed)
        self.assertFalse(post.search_engine_flagged)

        published = PublishedContent.objects.get(content_pk=tuto.pk)
        self.assertTrue(published.search_engine_already_indexed)
        self.assertFalse(published.search_engine_flagged)

        results = self.search_engine_manager.setup_search("*")
        number_of_results = sum(result["found"] for result in results)
        self.assertEqual(number_of_results, 4)  # get the 4 results back

    def tearDown(self):
        super().tearDown()

        # delete index:
        self.search_engine_manager.clear_index()
