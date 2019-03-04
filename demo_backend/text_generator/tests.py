from django.test import TestCase

# Create your tests here.

from .models import TextGenerator


class TextGeneratorModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        TextGenerator.objects.create(query='爱情')

    def test_query_content(self):
        t2p = TextGenerator.objects.get(id=1)
        expected_object_name = f'{t2p.query}'
        self.assertEquals(expected_object_name, '爱情')