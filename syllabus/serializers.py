from rest_framework import serializers
from .models import Exam, Subject, Topic, Subtopic, Concept
from progress.models import ConceptProgress

class ConceptSerializer(serializers.ModelSerializer):
    mastery = serializers.SerializerMethodField()
    raw_mastry = serializers.SerializerMethodField()
    last_practiced = serializers.SerializerMethodField()

    class Meta:
        model = Concept
        fields = [
            "id",
            "name",
            "description",
            "ai_meta",
            "mastery",
            "raw_mastry",
            "last_practiced",
        ]

    def get_mastery(self, obj):
        user = self.context.get("user")
        if not user or user.is_anonymous:
            return [0.0, 0.0]

        progress_dict = self.context.get("progress_dict")
        if progress_dict is not None:
            cp = progress_dict.get(obj.id)
        else:
            cp = ConceptProgress.objects.filter(user=user, concept=obj).first()
        return cp.get_mastery() if cp else [0.0, 0.0]

    def get_raw_mastry(self, obj):
        user = self.context.get("user")
        if not user or user.is_anonymous:
            return [0.0, 0.0]

        progress_dict = self.context.get("progress_dict")
        if progress_dict is not None:
            cp = progress_dict.get(obj.id)
        else:
            cp = ConceptProgress.objects.filter(user=user, concept=obj).first()
        return [
            round(cp.exam_readiness, 4),
            round(cp.chapter_understanding, 4),
        ] if cp else [0.0, 0.0]

    def get_last_practiced(self, obj):
        user = self.context.get("user")
        if not user or user.is_anonymous:
            return None

        progress_dict = self.context.get("progress_dict")
        if progress_dict is not None:
            cp = progress_dict.get(obj.id)
        else:
            cp = ConceptProgress.objects.filter(user=user, concept=obj).first()
        return cp.last_practiced if cp else None

class SubtopicSerializer(serializers.ModelSerializer):
    concepts = ConceptSerializer(many=True, read_only=True)

    class Meta:
        model = Subtopic
        fields = ["id", "name", "concepts"]


class TopicSerializer(serializers.ModelSerializer):
    subtopics = SubtopicSerializer(many=True, read_only=True)

    class Meta:
        model = Topic
        fields = ["id", "name",  "subtopics"]


class SubjectSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True)

    class Meta:
        model = Subject
        fields = ["id", "name",  "topics"]


class ExamSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ["id", "name", "exam_type", "subjects"]


class ConceptMiniSerializer(serializers.ModelSerializer):
    subject_id = serializers.IntegerField(source="subtopic.topic.subject.id", read_only=True)
    subject_name = serializers.CharField(source="subtopic.topic.subject.name", read_only=True)
    topic_id = serializers.IntegerField(source="subtopic.topic.id", read_only=True)
    topic_name = serializers.CharField(source="subtopic.topic.name", read_only=True)
    subtopic_id = serializers.IntegerField(source="subtopic.id", read_only=True)
    subtopic_name = serializers.CharField(source="subtopic.name", read_only=True)

    class Meta:
        model = Concept
        fields = [
            "id",
            "name",
            "subject_id",
            "subject_name",
            "topic_id",
            "topic_name",
            "subtopic_id",
            "subtopic_name",
        ]
