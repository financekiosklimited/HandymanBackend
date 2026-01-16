"""
Centralized constants for file upload limits and validation.
"""

# =============================================================================
# Attachment Type Choices
# =============================================================================

ATTACHMENT_TYPE_IMAGE = "image"
ATTACHMENT_TYPE_VIDEO = "video"
ATTACHMENT_TYPE_DOCUMENT = "document"

ATTACHMENT_TYPE_CHOICES = [
    (ATTACHMENT_TYPE_IMAGE, "Image"),
    (ATTACHMENT_TYPE_VIDEO, "Video"),
    (ATTACHMENT_TYPE_DOCUMENT, "Document"),
]

# =============================================================================
# File Size Limits (in bytes)
# =============================================================================

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
MAX_THUMBNAIL_SIZE = 500 * 1024  # 500KB

# =============================================================================
# Thumbnail Dimensions (in pixels)
# =============================================================================

MIN_THUMBNAIL_WIDTH = 200
MIN_THUMBNAIL_HEIGHT = 200

# =============================================================================
# File Count Limits
# =============================================================================

MAX_ATTACHMENTS_PER_REQUEST = 5
MAX_JOB_ATTACHMENTS = 10  # Max attachments per job
MAX_CHAT_ATTACHMENTS = 5  # Max attachments per chat message
MAX_JOB_APPLICATION_ATTACHMENTS = 10  # Max attachments per job application
MAX_REIMBURSEMENT_ATTACHMENTS = 5  # Max attachments per reimbursement

# =============================================================================
# Video Duration Limits (in seconds)
# =============================================================================

MAX_VIDEO_DURATION_SECONDS = 300  # 5 minutes

# =============================================================================
# Allowed MIME Types
# =============================================================================

ALLOWED_IMAGE_MIME_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
]

ALLOWED_VIDEO_MIME_TYPES = [
    "video/mp4",
    "video/quicktime",  # .mov
    "video/webm",
]

ALLOWED_DOCUMENT_MIME_TYPES = [
    "application/pdf",
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-powerpoint",  # .ppt
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
]

ALLOWED_ATTACHMENT_MIME_TYPES = (
    ALLOWED_IMAGE_MIME_TYPES + ALLOWED_VIDEO_MIME_TYPES + ALLOWED_DOCUMENT_MIME_TYPES
)

# =============================================================================
# File Extensions
# =============================================================================

ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"]
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".mov", ".webm"]
ALLOWED_DOCUMENT_EXTENSIONS = [
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
]
ALLOWED_ATTACHMENT_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS + ALLOWED_VIDEO_EXTENSIONS + ALLOWED_DOCUMENT_EXTENSIONS
)

# =============================================================================
# Upload Paths
# =============================================================================

JOB_ATTACHMENTS_UPLOAD_PATH = "jobs/attachments/%Y/%m/%d/"
CHAT_ATTACHMENTS_UPLOAD_PATH = "chat/attachments/%Y/%m/"
CHAT_THUMBNAILS_UPLOAD_PATH = "chat/thumbnails/%Y/%m/"
JOB_APPLICATION_ATTACHMENTS_UPLOAD_PATH = "job-applications/attachments/%Y/%m/%d/"
JOB_REIMBURSEMENT_ATTACHMENTS_UPLOAD_PATH = "reimbursements/attachments/%Y/%m/%d/"
WORK_SESSION_MEDIA_UPLOAD_PATH = "work-sessions/media/%Y/%m/%d/"
WORK_SESSION_THUMBNAILS_UPLOAD_PATH = "work-sessions/thumbnails/%Y/%m/%d/"
