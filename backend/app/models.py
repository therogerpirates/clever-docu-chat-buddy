
from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum, ForeignKey, Text, UUID, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()

class UserRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"

class RagType(enum.Enum):
    SQL = "sql"
    SEMANTIC = "semantic"

class FileType(enum.Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"

class FileStatus(enum.Enum):
    PROCESSING = "PROCESSING"
    READY = "READY"
    ERROR = "ERROR"
    
    @property
    def lowercase(self):
        return self.value.lower()

# Association table for file restrictions
file_restrictions = Table(
    'file_restrictions',
    Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id', ondelete="CASCADE")),
    Column('user_id', Integer, ForeignKey('users.id', ondelete="CASCADE"))
)

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    uploaded_files = relationship("File", back_populates="uploaded_by")
    restricted_files = relationship("File", secondary=file_restrictions, back_populates="restricted_users")

class File(Base):
    __tablename__ = "files"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_uuid = Column(UUID, unique=True, default=uuid.uuid4, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    rag_type = Column(Enum(RagType), nullable=True)
    description = Column(String, nullable=True)
    status = Column(Enum(FileStatus), nullable=False, default=FileStatus.PROCESSING)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    uploaded_by = relationship("User", back_populates="uploaded_files")
    restricted_users = relationship("User", secondary=file_restrictions, back_populates="restricted_files")
    processed_data = relationship("ProcessedData", back_populates="file", cascade="all, delete-orphan")
    pdf_document = relationship("PDFDocument", back_populates="file", uselist=False, cascade="all, delete-orphan")
    csv_document = relationship("CSVDocument", back_populates="file", uselist=False, cascade="all, delete-orphan")
    xlsx_document = relationship("XLSXDocument", back_populates="file", uselist=False, cascade="all, delete-orphan")

# ... keep existing code (ProcessedData, PDFDocument, PDFChunk, CSVDocument, CSVChunk, XLSXDocument, XLSXChunk classes)
class ProcessedData(Base):
    __tablename__ = "processed_data"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"))
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    file = relationship("File", back_populates="processed_data")

class PDFDocument(Base):
    __tablename__ = "pdf_documents"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), unique=True)
    title = Column(String, nullable=True)
    author = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    file = relationship("File", back_populates="pdf_document")
    chunks = relationship("PDFChunk", back_populates="document", cascade="all, delete-orphan")

class PDFChunk(Base):
    __tablename__ = "pdf_chunks"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("pdf_documents.id", ondelete="CASCADE"))
    page_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("PDFDocument", back_populates="chunks")

class CSVDocument(Base):
    __tablename__ = "csv_documents"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), unique=True)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    file = relationship("File", back_populates="csv_document")
    chunks = relationship("CSVChunk", back_populates="document", cascade="all, delete-orphan")

class CSVChunk(Base):
    __tablename__ = "csv_chunks"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("csv_documents.id", ondelete="CASCADE"))
    row_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("CSVDocument", back_populates="chunks")

class XLSXDocument(Base):
    __tablename__ = "xlsx_documents"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), unique=True)
    sheet_count = Column(Integer, nullable=False)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    file = relationship("File", back_populates="xlsx_document")
    chunks = relationship("XLSXChunk", back_populates="document", cascade="all, delete-orphan")

class XLSXChunk(Base):
    __tablename__ = "xlsx_chunks"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("xlsx_documents.id", ondelete="CASCADE"))
    sheet_name = Column(String, nullable=False)
    row_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("XLSXDocument", back_populates="chunks")
