from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class RegisterInput(BaseModel):
    username: str; email: str; password: str; confirmPassword: str


class LoginInput(BaseModel):
    username: str; password: str


class PasswordResetRequestInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class PasswordResetInput(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    newPassword: str
    confirmPassword: str


class CartInput(BaseModel):
    productId: int; quantity: int = Field(default=1, ge=1)


class UpdateCartInput(BaseModel):
    quantity: int = Field(ge=1)


class AddressInput(BaseModel):
    recipientName: str = Field(min_length=1, max_length=50)
    recipientPhone: str = Field(pattern=r"^1[3-9]\d{9}$")
    province: str = Field(min_length=2, max_length=20)
    city: str = Field(min_length=2, max_length=30)
    district: str = Field(min_length=2, max_length=30)
    detail: str = Field(min_length=2, max_length=120)


class CardInput(BaseModel):
    cardNumber: str = Field(min_length=12, max_length=25)


class OrderInput(BaseModel):
    itemIds: list[int]; deliveryService: str = "yto"; paymentType: str = "wechat"; paymentMethodId: int | None = None; address: AddressInput | None = None


class CommentInput(BaseModel):
    content: str = Field(min_length=1, max_length=20000); imageIds: list[int] = Field(default_factory=list)


class StockInput(BaseModel):
    quantity: int = Field(ge=1, le=10000)


class ProductCreateInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    quantity: int = Field(ge=1, le=10000)
    tagline: str = Field(default="", max_length=160)
    story: str = Field(default="", max_length=5000)
    imagePath: str | None = Field(default=None, max_length=255)


class ProductRelistInput(StockInput):
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PriceInput(BaseModel):
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    percent: int | None = Field(default=None)
    direction: str | None = Field(default=None)

    @field_validator("percent")
    @classmethod
    def valid_percent(cls, value: int | None) -> int | None:
        if value is not None and value not in {10, 20, 30}:
            raise ValueError("调价比例仅支持 10%、20% 或 30%")
        return value
