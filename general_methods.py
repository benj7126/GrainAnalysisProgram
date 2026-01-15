def conv(x):
    if isinstance(x, str):
        x = x.replace(',', '.')
        return round(float("0" if x == '' or x == '.' else x), 2)
    elif isinstance(x, float):
        return round(x, 2)
    elif isinstance(x, int):
        return round(float(x), 2)
    else:
        print("Conversion to float error for " + x)

def stringify(val):
    return "" if val == -1 else (str(val) if val != int(val) else str(int(val)))

def newline_strip(s):
    return s.replace('\n', ' ').replace('\r', '')

from contextlib import contextmanager

@contextmanager
def signals_blocked(widget):
    widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(False)

def get_list_item_or_none(my_list, index):
    try:
        return my_list[index]
    except:
        return None
    
from PyQt6.QtWidgets import QMessageBox
def yn_message_box(parent, title="Confirm", message="Are you sure?"):
    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No   # default button
    )
    return reply == QMessageBox.StandardButton.Yes

from PyQt6.QtWidgets import QMessageBox
def info_message_box(parent, title="Information", message="Done."): # TODO: replace QMessageBox.warning with this
    QMessageBox.information(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Ok
    )

def getLowerBound(list, hundred_stop):
    new_list = []

    for i in range(len(list)):
        if i == hundred_stop:
            new_list.append(max(list[i] - 5, 0))
        elif i < hundred_stop:
            new_list.append(max(list[i] - (10 if list[i] > 10 else 5), 0))
        else:
            new_list.append(list[i])


    return new_list

def getUpperBound(list, hundred_stop):
    new_list = []

    for i in range(len(list)):
        if list[i] == 0:
            new_list.append(0)
        elif i == hundred_stop:
            new_list.append(min(list[i] + 5, 100))
        elif i < hundred_stop:
            new_list.append(min(list[i] + (10 if list[i] > 10 else 5), 100))
        else:
            new_list.append(list[i])


    return new_list

def getUpperAndLower(list):
    hundred_stop = len(list)
    if list[len(list)-1] == 100:
        for i in range(len(list)-1, 0, -1):
            if (list[i] != 100):
                hundred_stop = i
                break
    return getUpperBound(list, hundred_stop), getLowerBound(list, hundred_stop)

from sql import get_session, Product, ProductSieve, SieveSize, UsedSand
def inner_create_new_product_or_update(list, id, rows, name=""):
    upper, lower = getUpperAndLower(list)
    with get_session() as session:
        try:
            product = session.query(Product).filter_by(product_id=id).first()
            if not product:
                product = Product(product_id=id, product_name=name)
                session.add(product)
            elif name != "":
                product.product_name = name

            for sieve_item in zip(list, lower, upper, range(len(list)-1, -1, -1)):
                sieve_limit = session.query(ProductSieve).filter_by(product_id=id, sieve=SieveSize(sieve_item[3])).first()
                if not sieve_limit:
                    sieve_limit = ProductSieve(product_id=id,sieve=SieveSize(sieve_item[3]))
                    session.add(sieve_limit)
                
                sieve_limit.target_percentage = conv(sieve_item[0])
                sieve_limit.lower_bound_percentage = conv(sieve_item[1])
                sieve_limit.upper_bound_percentage = conv(sieve_item[2])

            ## TODO: if i want it to only show how many percent is actually used?
            ## also need to fix the update thing to reflect the potential change in percent if i want this.

            sand_ids = sands.keys()
            total = sum([(conv(row[2]) if row[0] in sand_ids else 0) for row in rows])
            ## total = sum([conv(row[2]) for row in rows])

            # remove all sands, for if it is an update...
            old_sands = session.query(UsedSand).filter_by(used_in_product_id=id)
            for old_sand in old_sands:
                session.delete(old_sand)

            # store the sands used to create the product.
            for row in rows:
                article_number = row[0]
                product_designation = row[1]
                amount = conv(row[2])
                percent = round(((amount if row[0] in sand_ids else 0) / total) * 100, 2) ## if row[0] in sand_ids else 0

                session.add(UsedSand(
                    used_in_product_id = id,
                    item_id = article_number,
                    product_designation = product_designation,
                    amount = amount,
                    percent = percent
                ))
            

            session.commit()
        finally:
            session.close()

from sql import get_session, RawSandSieve
from local_data import sands
def sieve_data_from_components(componenets, sand_cache = {}):
    totals = [0]*10
    weight = 0

    sand_ids = sands.keys()

    with get_session() as session:
        try:
            for componenet in componenets:
                article_number = componenet[0]
                this_weight = componenet[2]
                if article_number in sand_ids:
                    if article_number not in sand_cache:
                        found_items = session.query(RawSandSieve).filter_by(item_id=article_number).all()

                        sand_cache[article_number] = []
                        for sieve_item in found_items:
                            sand_cache[article_number].append(sieve_item)
                    
                    for sieve_item in sand_cache[article_number]:
                        totals[sieve_item.sieve.value] += sieve_item.sieve_gram * this_weight

                    if len(sand_cache[article_number]) > 0:
                        weight += this_weight
        finally:
            session.close()

    if weight != 0:
        for i in range(10):
            totals[i] = round(totals[i] / weight, 2)
    
    return list(reversed(totals)), sand_cache

def update_product_with_used_sand(id):
    with get_session() as session:
        try:
            product = session.query(Product).filter_by(product_id=id).first()
            if not product:
                return
            
            used_sands = session.query(UsedSand).filter_by(used_in_product_id=id).all()

            # making a dict is not necessary, but you never know...
            components = list({s.item_id: [s.item_id, s.product_designation, s.amount] for s in used_sands}.values())
            
            list_data = sieve_data_from_components(components)[0]

            inner_create_new_product_or_update(list_data, id, components, product.product_name)

            session.commit()
        finally:
            session.close()