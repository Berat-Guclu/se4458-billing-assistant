# Mobile Provider Billing Guide

This guide is fictitious documentation for the billing assistant. It is not the billing database. Live totals, usage, and payments come from the billing API. The guide is split into sections and indexed once when the documentation server starts.

## 1. Monthly allowances

Each calendar month has its own allowance. The first 1,000 phone minutes in that month are included. The internet allowance is 20 GB. In this guide, 1 GB = 1,000 MB, so 20 GB = 20,000 MB. The usage operation records phone in steps of 10 minutes and internet in steps of 1 MB. Minutes and megabytes are added together for the month before a bill is calculated.

## 2. Phone pricing

Phone has no separate monthly plan charge. The first 1,000 minutes are free. After that, each started block of 1,000 minutes costs $10. A started block counts as soon as the subscriber enters it, even by one minute.

Examples: 1,000 minutes cost $0. 1,001 minutes cost $10. 2,000 minutes still cost $10. 2,001 minutes cost $20. Unused phone minutes do not reduce the internet charge.

## 3. Internet pricing

### 3.1 Included data

The included internet allowance is 20 GB, which is 20,000 MB. Megabytes inside that allowance do not add another data block. The plan charge that covers this allowance is stated in section 3.2.

### 3.2 Extra data charges

The extra internet cost is $10 for each started 10 GB block after the included 20 GB. The internet plan charge is $50 up to 20 GB, and the extra internet cost is added after that. A 10 GB block is 10,000 MB. A started block counts as soon as the subscriber enters it.

Example: 35 GB is 15 GB over the allowance. Fifteen GB fills two started 10 GB blocks, so the extra internet cost is $20. The internet charge is $50 + $20 = $70. 20 GB or less stays at $50. 20,001 MB is one extra block and the internet charge is $60. 40,000 MB is two extra blocks and the internet charge is $70. 40,001 MB is three extra blocks and the internet charge is $80.

## 4. Billing cycle

A bill belongs to one calendar month and year. The due date is the 15th day of the following month. Usage recorded after the bill is calculated is left out until the bill is calculated again. The summary shows the total, the paid amount, the remaining balance, and a status of UNPAID, PARTIAL, or PAID. The summary can be requested with a subscriber number. Detailed usage needs the subscriber's own login.

## 5. Partial payments

Partial payment rules: a subscriber may pay less than the remaining balance. The unpaid part stays open until another payment covers it. Each payment must send a new transaction ID. Sending the same transaction ID again is rejected as a duplicate. A payment larger than the remaining balance is rejected. No bank card is charged. Payments in this project are simulated.

## 6. Disputes

A subscriber may dispute usage within 30 days of the bill date. Opening a dispute does not delete the live bill and does not change the remaining balance by itself. Customer care applies the outcome after review. The assistant should read the bill detail before explaining a dispute, and it should say that a dispute is still open when no adjustment is in the live total.

## 7. Late payments

A late payment is any remaining balance after the due date. The late payment fee is $15 or 5 percent of the remaining balance, whichever is smaller. Calculating a bill does not add this fee by itself. The stored bill total contains only the phone blocks and the internet charge. If the live total does not contain the late payment fee, the assistant must not invent it on top of the API result.

## 8. Payment instructions

The assistant must ask the subscriber to reply CONFIRM before it records a payment. A typed subscriber number does not authorize access to another person's detailed usage or payments. The assistant can use only the subscriber who is logged in. Simulated payments keep the remaining balance and reject a duplicate transaction ID.
