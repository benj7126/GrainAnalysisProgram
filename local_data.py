from sqlalchemy import event
from sqlalchemy.orm import Session
from sql import get_session, Base, Product, ProductSieve, Customer, Batch, BatchSieve, RawSand, RawSandSieve

# should make sure to delete sieve too when deleting a product/batch

# do i want to / how do i add variables to the lambdas..?

def run_event(events, target):
    for event in events:
        if not callable(event):
            if event[0](target):
                event[1]()
        else:
            event()

products = {} # id -> [{name:name, batches:{batch_ids}]]

product_events = []
def add_product_event(event):
    product_events.append(event)

def product_change_update(target):
    if target.product_id not in products:
        products[target.product_id] = {"name":"", "batches":set()}

    products[target.product_id]["name"] = target.product_name
    
    run_event(product_events, target)

def product_remove(target):
    if target.product_id in products:
        del products[target.product_id]

    # TODO: do we also delete sieve data and batches here?
    
    run_event(product_events, target)

product_sieve_events = []
def add_product_sieve_event(event):
    product_sieve_events.append(event)

def product_sieve_change_update(target):
    run_event(product_sieve_events, target)

batches = {} # batch_id -> set(batch_iids)

batch_events = []
def add_batch_event(event):
    batch_events.append(event)

def batch_change_update(target):
    if target.batch_id not in batches.keys():
        batches[target.batch_id] = set()

    # ensure batch_iid in batch
    batches[target.batch_id].add(target.batch_iid)
    
    # ensure batch in products list
    if target.product_id in products:
        products[target.product_id]["batches"].add(target.batch_id)

    run_event(batch_events, target)

def batch_remove(target):
    if target.batch_id in batches:
        batches[target.batch_id].discard(target.batch_iid)

        if len(batches[target.batch_id]) == 0:
            del batches[target.batch_id]
    
    if target.product_id in products:
        products[target.product_id]["batches"].discard(target.batch_id)

    run_event(batch_events, target)

    ## should remove the sieve stuff from sql

batch_sieve_events = []
def add_batch_sieve_event(event):
    batch_sieve_events.append(event)

def batch_sieve_change_update(target):
    run_event(batch_sieve_events, target)

customers = set() # names

customer_events = []
def add_customer_event(event):
    customer_events.append(event)

def customer_change_update(target):
    customers.add(target.customer_name)

    run_event(customer_events, target)

def customer_remove(target):
    customers.discard(target.customer_name)

    run_event(customer_events, target)

sands = {} # item_id -> product_designation

sand_events = []
def add_sand_event(event):
    sand_events.append(event)

def sand_change_update(target):
    sands[target.item_id] = target.product_designation

    run_event(sand_events, target)

def sand_remove(target):
    if target.item_id in sands:
        del sands[target.item_id]

    run_event(sand_events, target)

sand_sieve_events = []
def add_sand_sieve_event(event):
    sand_sieve_events.append(event)

def sand_sieve_change_update(target):
    run_event(sand_sieve_events, target)

POST_COMMIT_INSERT_UPDATE_ACTIONS = {
    Product: product_change_update,
    ProductSieve: product_sieve_change_update,
    Batch: batch_change_update,
    BatchSieve: batch_sieve_change_update,
    Customer: customer_change_update,
    RawSand: sand_change_update,
    RawSandSieve: sand_sieve_change_update,
}

POST_COMMIT_DELETE_ACTIONS = {
    Product: product_remove,
    Batch: batch_remove,
    Customer: customer_remove,
    RawSand: sand_remove,
}

# artfact from wanting to make them update live
@event.listens_for(Base, 'after_update', propagate=True)
@event.listens_for(Base, 'after_insert', propagate=True)
def generic_after_insert_collector(mapper, connection, target):
    session = Session.object_session(target)
    if type(target) in POST_COMMIT_INSERT_UPDATE_ACTIONS:
        if not hasattr(session, '_pending_inserts_updates_for_post_commit'):
            session._pending_inserts_updates_for_post_commit = []
        session._pending_inserts_updates_for_post_commit.append(target)

@event.listens_for(Base, 'after_delete', propagate=True)
def generic_after_delete_collector(mapper, connection, target):
    session = Session.object_session(target)
    if type(target) in POST_COMMIT_DELETE_ACTIONS:
        if not hasattr(session, '_pending_deletes_for_post_commit'):
            session._pending_deletes_for_post_commit = []
        session._pending_deletes_for_post_commit.append({'obj_type': type(target), 'target': target})

@event.listens_for(Session, 'after_commit')
def generic_after_commit_dispatcher(session: Session):
    if hasattr(session, '_pending_inserts_updates_for_post_commit'):
        for obj in session._pending_inserts_updates_for_post_commit:
            action_func = POST_COMMIT_INSERT_UPDATE_ACTIONS.get(type(obj))
            if action_func:
                action_func(obj)
            else:
                print(f"WARNING: No insert action found for committed object of type {type(obj).__name__}.")
        del session._pending_inserts_updates_for_post_commit

    if hasattr(session, '_pending_deletes_for_post_commit'):
        for item in session._pending_deletes_for_post_commit:
            obj_type = item['obj_type']
            target = item['target']
            action_func = POST_COMMIT_DELETE_ACTIONS.get(obj_type)
            if action_func:
                action_func(target)
            else:
                print(f"WARNING: No delete action found for committed object of type {obj_type.__name__}.")
        del session._pending_deletes_for_post_commit

reload_events = []
def addReloadEvent(event):
    reload_events.append(event)

def load_data():
    with get_session() as session:
        products.clear()
        batches.clear()
        customers.clear()
        sands.clear()

        # products = {} # id -> [{name:name, batches:{batch_ids}]]
        query_product = session.query(Product.product_id, Product.product_name).all()

        for data in query_product:
            products[data[0]] = {"name":data[1], "batches":set()}

        # batches = {} # batch_id -> set(batch_iids)
        query_batches = session.query(Batch.batch_id, Batch.batch_iid, Batch.production_area, Batch.product_id).all()

        for data in query_batches:
            if data[0] not in batches.keys():
                batches[data[0]] = set()

            # ensure batch_iid in batch
            batches[data[0]].add(data[1])
            
            # ensure batch in products list
            if products[data[3]]:
                products[data[3]]["batches"].add(data[0])
        
        # customers = set() # names
        query_customers = session.query(Customer.customer_name).all()

        for data in query_customers:
            customers.add(data[0])
            
        # sands = {} # ids -> names
        query_sands = session.query(RawSand.item_id, RawSand.product_designation).all()

        for data in query_sands:
            sands[data.item_id] = data.product_designation
        
        session.close()
    for event in reload_events: event()

#actually set up data
load_data()