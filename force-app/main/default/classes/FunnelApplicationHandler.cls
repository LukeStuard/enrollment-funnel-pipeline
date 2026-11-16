/**
 * After-insert and after-update logic for Application__c.
 *
 * 1. Lead conversion: when an applicant's first Application is created, any open
 *    Lead with status "Application Started" and the applicant's email is converted
 *    into the applicant's existing Contact (no Opportunity).
 * 2. Live stage logging: writes a Stage_Event__c for new Applications (except
 *    generator records, which carry their own backdated history) and for every
 *    Status__c change.
 *
 * Runs in system mode on purpose (without sharing, plus explicit "as system" DML
 * and WITH SYSTEM_MODE queries, since API 67.0+ defaults to user mode): this is
 * internal plumbing, not a user-facing entry point. Conversion has to see the
 * matching Lead no matter who owns it, and stage events are written no matter
 * who made the change.
 */
public without sharing class FunnelApplicationHandler {

    // Database.convertLead accepts at most 100 LeadConvert objects per call.
    private static final Integer CONVERT_CHUNK_SIZE = 100;

    public static void handleAfterInsert(List<Application__c> newApps) {
        logInserted(newApps);
        convertMatchingLeads(newApps);
    }

    public static void handleAfterUpdate(List<Application__c> newApps, Map<Id, Application__c> oldMap) {
        List<Stage_Event__c> events = new List<Stage_Event__c>();
        for (Application__c app : newApps) {
            Application__c old = oldMap.get(app.Id);
            if (app.Status__c == old.Status__c) {
                continue;
            }
            String toStage = FunnelStages.forApplicationStatus(app.Status__c);
            if (toStage == null) {
                continue;
            }
            Stage_Event__c e = FunnelStages.liveEvent(FunnelStages.forApplicationStatus(old.Status__c), toStage);
            e.Application__c = app.Id;
            e.Contact__c = app.Applicant__c;
            events.add(e);
        }
        if (!events.isEmpty()) {
            insert as system events;
        }
    }

    private static void logInserted(List<Application__c> newApps) {
        List<Stage_Event__c> events = new List<Stage_Event__c>();
        for (Application__c app : newApps) {
            // The generator writes its own backdated history for synthetic records.
            if (String.isNotBlank(app.Synthetic_Key__c)) {
                continue;
            }
            String toStage = FunnelStages.forApplicationStatus(app.Status__c);
            if (toStage == null) {
                continue;
            }
            Stage_Event__c e = FunnelStages.liveEvent(null, toStage);
            e.Application__c = app.Id;
            e.Contact__c = app.Applicant__c;
            events.add(e);
        }
        if (!events.isEmpty()) {
            insert as system events;
        }
    }

    private static void convertMatchingLeads(List<Application__c> newApps) {
        Set<Id> newAppIds = new Set<Id>();
        Set<Id> contactIds = new Set<Id>();
        for (Application__c app : newApps) {
            newAppIds.add(app.Id);
            if (app.Applicant__c != null) {
                contactIds.add(app.Applicant__c);
            }
        }
        if (contactIds.isEmpty()) {
            return;
        }

        // Only an applicant's first Application converts their Lead.
        for (AggregateResult ar : [
            SELECT Applicant__c applicant
            FROM Application__c
            WHERE Applicant__c IN :contactIds AND Id NOT IN :newAppIds
            WITH SYSTEM_MODE
            GROUP BY Applicant__c
        ]) {
            contactIds.remove((Id) ar.get('applicant'));
        }
        if (contactIds.isEmpty()) {
            return;
        }

        Map<String, Contact> contactsByEmail = new Map<String, Contact>();
        for (Contact c : [
            SELECT Id, AccountId, Email
            FROM Contact
            WHERE Id IN :contactIds AND Email != null AND AccountId != null
            WITH SYSTEM_MODE
        ]) {
            contactsByEmail.put(c.Email.toLowerCase(), c);
        }
        if (contactsByEmail.isEmpty()) {
            return;
        }

        List<Lead> leads = [
            SELECT Id, Email
            FROM Lead
            WHERE IsConverted = false
                AND Status = :FunnelStages.LEAD_STATUS_APPLICATION_STARTED
                AND Email IN :contactsByEmail.keySet()
            WITH SYSTEM_MODE
        ];
        if (leads.isEmpty()) {
            return;
        }

        String convertedStatus = [
            SELECT MasterLabel
            FROM LeadStatus
            WHERE IsConverted = true
            WITH SYSTEM_MODE
            LIMIT 1
        ].MasterLabel;

        List<Database.LeadConvert> chunk = new List<Database.LeadConvert>();
        for (Lead l : leads) {
            Contact c = contactsByEmail.get(l.Email.toLowerCase());
            if (c == null) {
                continue;
            }
            Database.LeadConvert lc = new Database.LeadConvert();
            lc.setLeadId(l.Id);
            lc.setContactId(c.Id);
            lc.setAccountId(c.AccountId);
            lc.setConvertedStatus(convertedStatus);
            lc.setDoNotCreateOpportunity(true);
            lc.setOverwriteLeadSource(false);
            lc.setSendNotificationEmail(false);
            chunk.add(lc);
            if (chunk.size() == CONVERT_CHUNK_SIZE) {
                convert(chunk);
                chunk = new List<Database.LeadConvert>();
            }
        }
        if (!chunk.isEmpty()) {
            convert(chunk);
        }
    }

    private static void convert(List<Database.LeadConvert> chunk) {
        for (Database.LeadConvertResult r : Database.convertLead(chunk, false)) {
            if (!r.isSuccess()) {
                System.debug(LoggingLevel.WARN, 'Funnel lead conversion failed for ' + r.getLeadId() + ': ' + r.getErrors());
            }
        }
    }
}
