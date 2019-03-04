# coding:utf8

import os
import json
import tensorflow as tf

from rest_framework import generics
from .models import TextGenerator
from .serializers import TextGeneratorSerializer
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from .generator import generate_text


class ListTextGenerator(generics.ListCreateAPIView):
    queryset = TextGenerator.objects.all()
    serializer_class = TextGeneratorSerializer


class DetailTextGenerator(generics.RetrieveUpdateDestroyAPIView):
    queryset = TextGenerator.objects.all()
    serializer_class = TextGeneratorSerializer


@csrf_exempt
def generate(request):
    if request.method == 'POST':
        resp = json.loads(request.body)
        query = resp['query']
        try:
            task = generate_text.delay(query)
            text = task.get()
        except Exception as e:
            print('Reason for process: ', e)
            return HttpResponse(10000) # process wrong

        db_instance = TextGenerator(query=query, text=text)
        db_instance.save()
        return JsonResponse({"text": text})
    else:
        print("error, request should use POST")
        return HttpResponse("POST needed")

