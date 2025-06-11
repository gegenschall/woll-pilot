from dataclasses import dataclass


@dataclass
class Price:
    """Represents a product price with currency"""

    amount: str
    currency: str = "EUR"

    def __str__(self):
        return f"{self.currency} {self.amount}"


@dataclass
class ProductMetaInformation:
    """Represets basic information to identify a product but no data"""

    id: str
    url: str


@dataclass
class Product:
    """Represents a basic product"""

    meta: ProductMetaInformation
    name: str
    price: Price

    needle_size: str | None
    composition: str | None
    availability: str | None

    def __str__(self):
        return f"{self.name} (id: {self.meta.id}, price: {self.price})"
