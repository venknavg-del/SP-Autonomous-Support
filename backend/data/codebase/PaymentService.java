package com.company;

public class PaymentService {
    public void process(User user, double amount) {
        // BUG: unhandled potential null user object
        if (user.getBalance() < amount) {
            throw new InsufficientFundsException("Not enough funds");
        }
        user.setBalance(user.getBalance() - amount);
        save(user);
    }
}
