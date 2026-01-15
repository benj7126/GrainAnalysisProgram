from sqlalchemy import (Column, Integer, String, Float, Date, ForeignKey, Text, create_engine)
from sqlalchemy import Enum as SQLAlchemyEnum, ForeignKeyConstraint
from sqlalchemy.orm import  sessionmaker, declarative_base
import enum

# TODO: make most strings varchars?

class SieveSize(enum.Enum):
    S16mm = 0
    S8mm = 1
    S4mm = 2
    S2mm = 3
    S1mm = 4
    S0_5mm = 5
    S0_25mm = 6
    S0_125mm = 7
    S0_075mm = 8 # TODO: change to 0.09
    Bund = 9

Base = declarative_base()

# 2. Define a single, simple model
class Product(Base):
    __tablename__ = 'products'

    product_id = Column(Text, primary_key=True)
    product_name = Column(Text, nullable=False)
    remarks = Column(Text)

class ProductSieve(Base):
    __tablename__ = 'product_sieve_limits'

    product_id = Column(Text, ForeignKey('products.product_id'), primary_key=True)
    sieve = Column(SQLAlchemyEnum(SieveSize), primary_key=True, nullable=False)
    target_percentage = Column(Float)
    lower_bound_percentage = Column(Float)  
    upper_bound_percentage = Column(Float)

class Customer(Base):
    __tablename__ = 'customers'

    customer_name = Column(Text, primary_key=True)
    customer_id = Column(String(2)) # should be able to tell batch based on this.
    address = Column(Text)
    postal = Column(String(4))
    city = Column(Text)

class Batch(Base):
    __tablename__ = 'batches'

    batch_id = Column(Text, primary_key=True)
    batch_iid = Column(Text, primary_key=True) # you can have multiple of each batch
    product_id = Column(Text, ForeignKey('products.product_id'))
    production_area = Column(Integer)
    customer_name = Column(Text) # dosent have to match | but if it does it can be used, TODO: or maby it does..?
    production_date = Column(Date)
    powder_percentage = Column(Float)
    density = Column(Float)
    preformed_by = Column(Text)

class BatchSieve(Base):
    __tablename__ = 'batch_sieve_results'

    batch_id = Column(Text, primary_key=True)
    batch_iid = Column(Text, primary_key=True)
    production_area = Column(Integer)
    sieve = Column(SQLAlchemyEnum(SieveSize), primary_key=True, nullable=False)
    sieve_gram = Column(Float)

    __table_args__ = (
        ForeignKeyConstraint(
            ['batch_id', 'batch_iid'],
            ['batches.batch_id', 'batches.batch_iid']
        ),
    )

class RawSand(Base):
    __tablename__ = 'raw_sands'
    
    item_id = Column(String(9), primary_key=True)
    product_designation = Column(Text)

class RawSandSieve(Base):
    __tablename__ = 'raw_sand_sieves'

    item_id = Column(String(9), ForeignKey('raw_sands.item_id'), primary_key=True)
    sieve = Column(SQLAlchemyEnum(SieveSize), primary_key=True, nullable=False)
    sieve_gram = Column(Float)

class UsedSand(Base):
    __tablename__ = 'used_sands'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    used_in_product_id = Column(Text, ForeignKey('products.product_id'))
    item_id = Column(String(9), ForeignKey('raw_sands.item_id'))
    product_designation = Column(Text)
    amount = Column(Float)
    percent = Column(Float)

service = "mysql+mysqldb"
username = "user"
password = "userpassword"
ip = "localhost"
port = "3306"
database = "example_db"

connection_string = f'{service}://{username}:{password}@{ip}:{port}/{database}' # Connect to database
connection_string = "sqlite:///:memory:" # In-memory database
connection_string = "sqlite:///database.db" # File-based database

engine = create_engine(connection_string, echo=False)

if __name__ == "__main__": # create tables if this file is run explicitly
    Base.metadata.create_all(engine)
    exit()

# Create a session class
# autocommit=False means transactions need to be explicitly committed (session.commit())
# autoflush=False means objects aren't flushed to the database automatically until commit or query
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    return SessionLocal()