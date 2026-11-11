#===============================================================================
#                                   INCLUDES
#===============================================================================
from __future__ import annotations
from dataclasses import dataclass
from lark import Lark, Token, Tree
from lark.exceptions import LarkError
from pathlib import Path

import argparse

from sqlalchemy import String, Float, Integer, create_engine, select
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from collections.abc import Sequence
#===============================================================================
#                                   DATA MODEL
#===============================================================================
@dataclass
class Product:
    name: str
    price: float
    stock: int

products: dict[str, Product] = {
    "monorail": Product(name="Monorail", price=1449.99, stock=30),
    "hewlett_packard": Product(name="Hewlett Packard", price=1849.99, stock=23),
    "compaq": Product(name="COMPAQ", price=2399.99, stock=8),
}

#===============================================================================
#                               DATABASE INTERFACE
#===============================================================================
class DatabaseModel(DeclarativeBase):
    pass

class ProductModel(DatabaseModel):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer)

    @staticmethod
    def to_model(product: Product)->ProductModel:
        return ProductModel(name=product.name, price=product.price, stock=product.stock)


    def from_model(self)->Product:
        return Product(name=self.name, price=self.price, stock=self.stock)


def prepare_db()->Engine:    
    engine = create_engine("sqlite:///local/demo.db")
    DatabaseModel.metadata.create_all(engine)
    return engine


def populate_db(eng: Engine)->None:
    with Session(eng) as session:
        existing_products = session.scalars(select(ProductModel)).first()

        if existing_products is not None:
            return

        for product in products.values():
            session.add(ProductModel.to_model(product))

        session.commit()


def clear_db(eng: Engine)->None:
    with Session(eng) as session:
        session.query(ProductModel).delete(synchronize_session="fetch")
        session.commit()


def retrieve_product_by_name(eng: Engine, name: str)->list[Product]:
    prods: list[Product] = []
    with Session(eng) as session:
        products: Sequence[ProductModel] = session.scalars(select(ProductModel).where(ProductModel.name.ilike(name))).all()
        for product in products:
            prods.append(product.from_model())
    return prods


def add_product(eng: Engine, name: str, price: float, stock: int)->bool:
    with Session(eng) as session:
        existing_product = session.scalars(select(ProductModel).where(ProductModel.name.ilike(name))).first()

        if existing_product is not None:
            return False

        product = ProductModel(name=name, price=price, stock=stock)
        session.add(product)
        session.commit()

        return True


def get_all_products(eng: Engine)-> list[Product]:
    prods: list[Product] = []
    with Session(eng) as session:
        products = session.scalars(select(ProductModel)).all()
        for product in products:
            prods.append(product.from_model())
    return prods


def update_product(eng: Engine, name: str, new_name: str, new_price: float, new_stock: int)->bool:
    with Session(eng) as session:
        product = session.scalars(select(ProductModel).where(ProductModel.name.ilike(name))).first()

        if product is None:
            return False

        product.name = new_name
        product.price = new_price
        product.stock = new_stock

        session.commit()
        return True


def delete_product(eng: Engine, name: str)->bool:
    with Session(eng) as session:
        product = session.scalars(select(ProductModel).where(ProductModel.name.ilike(name))).first()

        if product is None:
            return False

        session.delete(product)
        session.commit()
        return True

#===============================================================================
#                               MAIN FUNCTIONS
#===============================================================================
def admin_menu(eng: Engine)->None:
    while True:
        print("\n===== ADMIN MENU =====")
        print("0 - Close the admin panel")        
        print("1 - Add product")
        print("2 - Find product")
        print("3 - Update product")
        print("4 - Delete product")
        print("5 - List all products")
        print("6 - Clear database")

        user_input = input("Choose which action you want to perform: ").strip()
        if user_input == "1":
            print("ADDING A PRODUCT")

            name = input("Enter the product's name: ").strip()
            if not name:
                print("A product has to have a name. Please enter it")
                continue
            try:
                price = float(input("Enter the product's price: "))
                stock = int(input("Enter the product's stock amount: "))

                if price < 0 or stock < 0:
                    print("Price and stock cannot be less than zero!")
                    continue

                result = add_product(eng, name, price, stock)

                if result:
                    print("Product added successfully")
                else:
                    print("There already is a product with that name.")
            except ValueError:
                print("Price must be a number, and stock must be an integer.")

        elif user_input == "2":
            print("FINDING A PRODUCT")

            name = input("Enter the product's name: ").strip()

            if not name:
                print("You must enter the product's name!")
                continue

            result = retrieve_product_by_name(eng, name)

            if result:
                for product in result:
                    print(f"NAME: {product.name}")
                    print(f"PRICE: {product.price}")
                    print(f"STOCK: 1{product.stock}")
            else:
                print("Product not found.")

        elif user_input == "3":
            print("UPDATING PRODUCT")

            name = input("Enter the name of the product you want to update: ").strip()
            if not name:
                print("You must enter the product's name!")
                continue

            existing_product = retrieve_product_by_name(eng, name)

            if not existing_product:
                print("Product not found.")
                continue

            print("\nCURRENT PRODUCT INFO")
            print(f"{existing_product[0].name}")
            print(f"{existing_product[0].price}")
            print(f"{existing_product[0].stock}")

            new_name = input("Enter the new name for the product: ").strip()

            if not new_name:
                print("You must enter the new product name!")
                continue

            try:
                new_price = float(input("Enter a new price for the product: "))
                new_stock = int(input("Enter a new stock amount for the product: "))

                if new_price < 0 or new_stock < 0:
                    print("Both price and stock must be positive numbers!")
                    continue

                result = update_product(eng, name, new_name, new_price, new_stock)

                if result:
                    print("Product updated successfully.")
                else:
                    print("Product couldn't be changed.")
            except ValueError:
                print("Wrong price or stock! Try again.")

        elif user_input == "4":
            print("DELETING PRODUCT")

            name = input("Enter the product's name: ").strip()

            if not name:
                print("You must enter the product's name!")
                continue

            result = retrieve_product_by_name(eng, name)

            if not result:
                print("Product could not be found.")
                continue

            deleted = delete_product(eng, name)

            if deleted:
                print("Product was deleted successfully.")
            else:
                print("Product was not deleted. Something went wrong")

        elif user_input == "5":
            print("LISTING ALL PRODUCTS")

            products = get_all_products(eng)

            if not products:
                print("The database is empty.")
                continue

            for product in products:
                print("=============================")
                print(f"{product.name}")
                print(f"{product.price}")
                print(f"{product.stock}")
                
        elif user_input == "6":
            print("CLEARING THE DATABASE")
            clear_db(eng)
            print("The database was successfully cleared.")

        elif user_input == "0":
            print("Closing the admin panel")
            break
        else:
            print("Please choose a valid option")


def load_grammar(grammar_path: str)->str:
    try:
        return Path(grammar_path).read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(f"Could not load grammar file '{grammar_path}': {e}")

def process_query(query: str, grammar_path: str, eng: Engine) -> str:

    try:
        grammar = load_grammar(grammar_path)
        parser = Lark(grammar, parser="earley")

        tree = parser.parse(query)
        query_node: Tree | Token = tree.children[0]

        if isinstance(query_node, Token):
            return "ERROR"

        item_node = next(query_node.find_data("item"), None)

        if item_node is None:
            return "Could not identify the product."

        item_name = "_".join(
            str(token).lower()
            for token in item_node.children
            if isinstance(token, Token)
        )

        product_list = retrieve_product_by_name(eng, item_name.replace("_", " "))

        if not product_list:
            return f"Product '{item_name}' was not found."

        product = product_list[0]

        # Handle price question
        if query_node.data == "price_question":
            return (
                f"The price of {product.name} "
                f"is {product.price:.2f}."
            )

        # Handle availability question
        if query_node.data == "availability_question":

            if product.stock > 0:
                return f"Yes, {product.name} is in stock."

            return f"No, {product.name} is not in stock."

        # Handle stock question
        if query_node.data == "stock_question":
            return (
                f"There are {product.stock} units "
                f"of {product.name} in stock."
            )

        return "Unsupported question."

    except LarkError:
        return (
            "I could not understand your question. "
            "Please check its grammar and try again."
        )

    except Exception as e:
        return f"An unexpected error occurred: {e}"




#===============================================================================
#                                   MAIN
#===============================================================================

def main():
    eng = prepare_db()
    populate_db(eng)

    argument_parser = argparse.ArgumentParser()

    argument_parser.add_argument(
        "-g",
        "--grammar",
        type=str,
        default="src/talk_shop/grammar.txt",
        help="Path to grammar file."
    )

    args = argument_parser.parse_args()

    while True:
        print("\n===== TALK SHOP =====")
        print("1 - Admin Panel")
        print("2 - User Panel")
        print("0 - Exit")

        user_choice = input("Please choose the mode: ").strip()

        if user_choice == "1":
            admin_menu(eng)

        elif user_choice == "2":
            print("Type END to return to the main menu.")

            while True:
                query = input().strip()

                if query.upper() == "END":
                    break

                if not query:
                    print("You need to ask a question before continuing.")
                    continue

                print(process_query(query, args.grammar, eng))

        elif user_choice == "0":
            print("Closing Talk Shop.")
            break

        else:
            print("Invalid option. Choose again.")


if __name__ == "__main__":
    main()