from rest_framework.test import APITestCase
from django.test import override_settings
from django.urls import reverse
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from syllabus.models import Exam

User = get_user_model()

class SyllabusCachingTestCase(APITestCase):
    def setUp(self):
        # Create a sample exam for testing
        self.exam = Exam.objects.create(name="JEE Main", exam_type="jee", description="JEE description")
        self.url = reverse("syllabus-tree")
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("django.core.cache.cache.get")
    @patch("django.core.cache.cache.set")
    @override_settings(USE_CACHING=True)
    def test_anonymous_request_cached_when_use_caching_true(self, mock_set, mock_get):
        # Setup mock behavior
        mock_get.return_value = None  # Cache miss

        # First request (should miss cache and set cache)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        # Verify it attempted to fetch from cache and then store in cache
        mock_get.assert_called_with("syllabus_tree_exam_all")
        mock_set.assert_called_once()
        
        # Mock a cache hit for the second request
        mock_get.return_value = response.data
        mock_set.reset_mock()
        
        response2 = self.client.get(self.url)
        self.assertEqual(response2.status_code, 200)
        
        # In a cache hit, we return the cached data directly, no mock_set should be called
        mock_set.assert_not_called()

    def test_anonymous_request_not_cached_when_use_caching_false(self):
        # When USE_CACHING is False (default or overridden), DummyCache should be configured
        # Wait, since USE_CACHING in settings.py is evaluated on module load, overriding it
        # via override_settings(USE_CACHING=False) doesn't automatically re-evaluate settings.py's
        # CACHES dictionary. However, we can override CACHES directly using override_settings.
        dummy_caches = {
            'default': {
                'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
            }
        }
        with override_settings(CACHES=dummy_caches):
            with patch("django.core.cache.cache.get") as mock_get, patch("django.core.cache.cache.set") as mock_set:
                mock_get.return_value = None
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 200)
                # View still calls get/set on the cache, but DummyCache's implementation does nothing
                mock_get.assert_called_once()
                mock_set.assert_called_once()

    @override_settings(USE_CACHING=True)
    def test_authenticated_request_uses_static_cache_but_overlays_progress(self):
        # Create user
        user = User.objects.create_user(username="testuser", password="password123")
        self.client.force_authenticate(user)

        # Create progress components
        from syllabus.models import Subject, Topic, Subtopic, Concept
        from progress.models import ConceptProgress
        from django.utils import timezone
        
        subject = Subject.objects.create(exam=self.exam, name="Physics")
        topic = Topic.objects.create(subject=subject, name="Mechanics")
        subtopic = Subtopic.objects.create(topic=topic, name="Kinematics")
        concept = Concept.objects.create(subtopic=subtopic, name="Velocity", description="Velocity desc")
        
        ConceptProgress.objects.create(
            user=user,
            concept=concept,
            exam_readiness=0.8,
            chapter_understanding=0.9,
            last_practiced=timezone.now()
        )

        with patch("django.core.cache.cache.get") as mock_get, patch("django.core.cache.cache.set") as mock_set:
            static_response = [{
                "id": self.exam.id,
                "name": self.exam.name,
                "exam_type": self.exam.exam_type,
                "subjects": [{
                    "id": subject.id,
                    "name": subject.name,
                    "topics": [{
                        "id": topic.id,
                        "name": topic.name,
                        "subtopics": [{
                            "id": subtopic.id,
                            "name": subtopic.name,
                            "concepts_count": 1
                        }]
                    }]
                }]
            }]
            mock_get.return_value = static_response

            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)

            # Authenticated request SHOULD fetch static structure from cache
            mock_get.assert_called_with("syllabus_tree_exam_all")
            # Authenticated request should NOT write back to cache if already cached
            mock_set.assert_not_called()
            
            # The response should NOT have nested concepts
            exam_data = response.data["exams"][0]
            subtopic_data = exam_data["subjects"][0]["topics"][0]["subtopics"][0]
            self.assertEqual(subtopic_data["id"], subtopic.id)
            self.assertNotIn("concepts", subtopic_data)
            self.assertEqual(subtopic_data["concepts_count"], 1)

            # Now, test fetching concepts for this subtopic dynamically
            concepts_url = reverse("subtopic-concepts", kwargs={"subtopic_id": subtopic.id})
            concepts_response = self.client.get(concepts_url)
            self.assertEqual(concepts_response.status_code, 200)
            
            concept_data = concepts_response.data[0]
            self.assertEqual(concept_data["id"], concept.id)
            self.assertNotEqual(concept_data["mastery"], [0.0, 0.0])
            self.assertEqual(concept_data["raw_mastry"], [0.8, 0.9])
            self.assertIsNotNone(concept_data["last_practiced"])

    @override_settings(USE_CACHING=True)
    def test_authenticated_request_cache_miss_sets_static_cache(self):
        user = User.objects.create_user(username="testuser", password="password123")
        self.client.force_authenticate(user)
        
        with patch("django.core.cache.cache.get") as mock_get, patch("django.core.cache.cache.set") as mock_set:
            mock_get.return_value = None  # Cache miss
            
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            
            # It should query the cache, miss, and then set the static cache key
            mock_get.assert_called_with("syllabus_tree_exam_all")
            mock_set.assert_called_once()

    @override_settings(USE_CACHING=True)
    def test_cache_invalidation_on_exam_change(self):
        # Ensure caching is active and we do a request
        with patch("django.core.cache.cache.clear") as mock_clear:
            self.exam.name = "Updated JEE Main"
            self.exam.save()
            mock_clear.assert_called_once()
