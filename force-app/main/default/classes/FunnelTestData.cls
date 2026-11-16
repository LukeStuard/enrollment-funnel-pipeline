/**
 * Shared test helpers for the funnel triggers.
 *
 * Test DML runs in system mode with duplicate rules allowed to save:
 * - API 67.0+ defaults Apex to user mode, and the funnel fields are granted by
 *   a permission set rather than the profile, so user-mode test DML fails on FLS.
 * - The standard duplicate rules block a Lead whose email matches an existing
 *   Contact, which is exactly the case the conversion tests need.
 */
@IsTest
public class FunnelTestData {

    public static final String ACCOUNT_NAME = 'Funnel Test Applicants';

    public static Database.DMLOptions dmlOptions() {
        Database.DMLOptions opts = new Database.DMLOptions();
        opts.OptAllOrNone = true;
        opts.DuplicateRuleHeader.allowSave = true;
        return opts;
    }

    public static void insertAll(List<SObject> records) {
        Database.insert(records, dmlOptions(), AccessLevel.SYSTEM_MODE);
    }

    public static void updateAll(List<SObject> records) {
        Database.update(records, dmlOptions(), AccessLevel.SYSTEM_MODE);
    }

    public static Account account() {
        Account a = new Account(Name = ACCOUNT_NAME);
        insertAll(new List<SObject>{ a });
        return a;
    }

    public static Contact buildContact(Id accountId, String lastName, String email) {
        return new Contact(FirstName = 'Test', LastName = lastName, Email = email, AccountId = accountId);
    }

    public static Lead buildLead(String lastName, String email, String status) {
        return new Lead(FirstName = 'Test', LastName = lastName, Company = 'Prospective Student', Email = email, Status = status);
    }

    public static Application__c buildApp(Id contactId) {
        return new Application__c(Applicant__c = contactId, Program__c = 'MBA', Term__c = 'Fall 2026', Status__c = 'Draft');
    }
}
