# Shop vocabulary

## Comment

A customer-authored rich-text message attached to exactly one Product. A Comment may include zero or more Comment Images and preserves the author's display name at the time of posting.

## Comment Image

An image uploaded by an authenticated customer for use in a Comment. It is initially unbound, then becomes attached to one Comment when that customer publishes it. A Comment Image cannot be attached by another customer.

## Default Address

The account-level delivery address a customer may edit. It is used to prefill a checkout but is not itself historical order data.

## Order Delivery Snapshot

The immutable delivery choice and address captured for one Order. Changing the customer's Default Address cannot change an existing Order Delivery Snapshot.

## Delivery Service

The fulfillment option selected for an Order: store pickup, next-day SF Express, YTO Express, Guotong Express, STO Express, or Yunda Express. Store pickup and the four standard couriers are free; next-day SF Express costs ¥5.

## Pickup Location

The fixed store-pickup destination for an Order: 小行星桌游社 at 常州市天宁区文化广场, with the displayed contact number +86-12345678901. 常州市政务服务中心 is a map reference only and is not the pickup destination.

## Simulated Payment Method

The non-processing payment choice recorded for an Order: WeChat Pay, Alipay, or a saved bank card. It represents checkout intent only and never initiates a real payment.

## Order Notification

A delivery-facing Feishu interactive card sent proactively to the configured conversation. It contains an Order's identifier, items, customer account, full phone number, delivery service, and the appropriate pickup or delivery address. A failure to deliver this notification does not prevent Order creation; it remains pending retry, is first attempted asynchronously after creation, and is retried at service startup and every five minutes, for at most six attempts. The notification service does not receive Feishu events or callbacks.

## Management Dashboard

An administrator-only operational view of Orders, Products, Inventory, and Users. Its daily metrics use China Standard Time. Inventory in order and product statistics means the current remaining inventory, not a historical stock snapshot.
