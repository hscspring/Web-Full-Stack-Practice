from django.db import models

# Create your models here.

class TextGenerator(models.Model):
    # 用户输入的词，默认为空格，最大长度为 4
    query = models.CharField(default=' ', max_length=4)
    # 生成的文本
    text = models.TextField(default='')
    # 创建时间
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query