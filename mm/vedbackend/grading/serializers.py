from rest_framework import serializers


class UploadSerializer(
    serializers.Serializer
):
    question_paper = serializers.FileField()
    answer_sheet = serializers.FileField()

    def validate_question_paper(
        self,
        value,
    ):
        allowed = (
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
        )

        if not value.name.lower().endswith(
            allowed
        ):
            raise serializers.ValidationError(
                "Question paper must be PDF or image."
            )

        return value

    def validate_answer_sheet(
        self,
        value,
    ):
        allowed = (
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
        )

        if not value.name.lower().endswith(
            allowed
        ):
            raise serializers.ValidationError(
                "Answer sheet must be PDF or image."
            )

        return value


class StatusResponseSerializer(
    serializers.Serializer
):
    status = serializers.CharField()

    result = serializers.JSONField(
        required=False,
        allow_null=True,
    )

    error = serializers.CharField(
        required=False,
        allow_null=True,
    )

    progress = serializers.JSONField(
        required=False,
        allow_null=True,
    )