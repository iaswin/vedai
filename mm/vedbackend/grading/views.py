import threading
import uuid

from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser

from .serializers import (
    UploadSerializer,
)

from .pdf import file_to_images

from .storage import (
    save_assessment,
    get_assessment,
)

from .pipeline import run_pipeline


# ============================================================
# UPLOAD
# ============================================================

class UploadView(APIView):

    parser_classes = [
        MultiPartParser
    ]

    def post(self, request):

        serializer = UploadSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        question_file = serializer.validated_data[
            "question_paper"
        ]

        answer_file = serializer.validated_data[
            "answer_sheet"
        ]

        try:

            question_pages = file_to_images(
                question_file.read(),
                question_file.name,
            )

            answer_pages = file_to_images(
                answer_file.read(),
                answer_file.name,
            )

        except Exception as exc:

            return Response(
                {
                    "error": f"Could not process files: {exc}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not question_pages:

            return Response(
                {
                    "error": "Question paper contains no pages."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not answer_pages:

            return Response(
                {
                    "error": "Answer sheet contains no pages."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = str(uuid.uuid4())

        save_assessment(
            session_id,
            {
                "status": "queued",

                "progress": {
                    "percent": 0,
                    "stage": "queued",
                },

                "qp_pages": question_pages,

                "ans_pages": answer_pages,

                "result": None,

                "error": None,
            },
        )

        thread = threading.Thread(
            target=run_pipeline,
            args=(session_id,),
            daemon=True,
        )

        thread.start()

        return Response(
            {
                "session_id": session_id,
                "status": "queued",
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# STATUS
# ============================================================

class StatusView(APIView):

    def get(
        self,
        request,
        session_id,
    ):

        data = get_assessment(
            session_id
        )

        if not data:

            return Response(
                {
                    "error": "Session not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "session_id": session_id,

                "status": data.get(
                    "status",
                    "unknown",
                ),

                "result": data.get(
                    "result"
                ),

                "error": data.get(
                    "error"
                ),

                "progress": data.get(
                    "progress",
                    {
                        "percent": 0,
                        "stage": "queued",
                    },
                ),
            }
        )


# ============================================================
# PAGE IMAGE
# ============================================================

class PageImageView(APIView):

    def get(
        self,
        request,
        session_id,
        doc,
        page_num,
    ):

        data = get_assessment(
            session_id
        )

        if not data:

            return Response(
                {
                    "error": "Session not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if doc == "question":

            pages = data.get(
                "qp_pages",
                []
            )

        elif doc == "answer":

            pages = data.get(
                "ans_pages",
                []
            )

        else:

            return Response(
                {
                    "error": "Invalid document type."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            page_number = int(page_num)

        except (ValueError, TypeError):

            return Response(
                {
                    "error": "Invalid page number."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        page = next(
            (
                p
                for p in pages
                if p.get("page_number") == page_number
            ),
            None,
        )

        if not page:

            return Response(
                {
                    "error": "Page not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return HttpResponse(
            page["png_bytes"],
            content_type="image/png",
        )


# ============================================================
# HEALTH
# ============================================================

class HealthView(APIView):

    def get(self, request):

        return Response(
            {
                "status": "ok"
            }
        )