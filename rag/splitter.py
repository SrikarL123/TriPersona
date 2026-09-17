import re

from langchain_text_splitters import RecursiveCharacterTextSplitter


SECTION_ALIASES = {
    "projects": [
        "projects",
        "project",
        "academic projects",
        "personal projects",
        "key projects",
        "selected projects",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "work history",
        "employment",
        "internship experience",
        "internships",
    ],
    "education": [
        "education",
        "academic background",
        "academic qualifications",
        "qualifications",
    ],
    "skills": [
        "skills",
        "technical skills",
        "technical expertise",
        "technologies",
        "tech stack",
    ],
    "achievements": [
        "achievements",
        "accomplishments",
        "awards",
        "certifications",
        "honors",
    ],
}


def normalize_heading(text):
    text = re.sub(r"[^a-zA-Z0-9\s/&-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def detect_heading_section(line):
    """
    Detect whether a line looks like a resume section heading.
    """

    normalized = normalize_heading(line)

    if not normalized:
        return None

    # Exact heading match.
    for section, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if normalized == alias:
                return section

    return None


def annotate_sections(document):
    """
    Add section metadata to a LangChain Document before splitting.

    The current section is carried forward, so chunks following a heading
    inherit that section until another heading appears.
    """

    text = document.page_content or ""

    lines = text.splitlines()

    current_section = "general"
    annotated_lines = []

    for line in lines:

        heading_section = detect_heading_section(line)

        if heading_section:
            current_section = heading_section

        annotated_lines.append(
            line
        )

    document.page_content = "\n".join(
        annotated_lines
    )

    document.metadata["document_section"] = current_section

    return document


def split_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )

    chunks = []

    for document in documents:

        text = document.page_content or ""

        if not text.strip():
            continue

        lines = text.splitlines()

        current_section = "general"
        section_blocks = []
        current_lines = []

        for line in lines:

            heading_section = detect_heading_section(
                line
            )

            if heading_section and current_lines:

                section_blocks.append(
                    (
                        current_section,
                        "\n".join(current_lines)
                    )
                )

                current_lines = []

            if heading_section:
                current_section = heading_section

            current_lines.append(line)

        if current_lines:
            section_blocks.append(
                (
                    current_section,
                    "\n".join(current_lines)
                )
            )

        # If no section headings were detected, split normally.
        if not section_blocks:
            section_blocks = [
                ("general", text)
            ]

        for section, block_text in section_blocks:

            if not block_text.strip():
                continue

            block_document = document.model_copy(
                deep=True
            )

            block_document.page_content = block_text
            block_document.metadata = dict(
                document.metadata
            )
            block_document.metadata["section"] = section

            block_chunks = splitter.split_documents(
                [block_document]
            )

            for chunk in block_chunks:
                chunk.metadata["section"] = section
                chunks.append(chunk)

    return chunks
