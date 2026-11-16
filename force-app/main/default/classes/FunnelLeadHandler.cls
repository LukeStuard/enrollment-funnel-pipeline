/**
 * Live stage logging for Lead: a Stage_Event__c when a Lead is created (except
 * generator records, which carry their own backdated history) and when its
 * Status changes. Conversion is not logged here; the Application side records
 * the applicant stage.
 *
 * Runs in system mode on purpose (API 67.0+ defaults to user mode): logging
 * must not depend on the permissions of whoever changed the Lead.
 */
public without sharing class FunnelLeadHandler {

    public static void handleAfterInsert(List<Lead> newLeads) {
        List<Stage_Event__c> events = new List<Stage_Event__c>();
        for (Lead l : newLeads) {
            if (String.isNotBlank(l.Synthetic_Key__c)) {
                continue;
            }
            String toStage = FunnelStages.forLeadStatus(l.Status);
            if (toStage == null) {
                continue;
            }
            Stage_Event__c e = FunnelStages.liveEvent(null, toStage);
            e.Lead__c = l.Id;
            events.add(e);
        }
        if (!events.isEmpty()) {
            insert as system events;
        }
    }

    public static void handleAfterUpdate(List<Lead> newLeads, Map<Id, Lead> oldMap) {
        List<Stage_Event__c> events = new List<Stage_Event__c>();
        for (Lead l : newLeads) {
            Lead old = oldMap.get(l.Id);
            if (l.Status == old.Status) {
                continue;
            }
            if (l.IsConverted && !old.IsConverted) {
                continue;
            }
            String toStage = FunnelStages.forLeadStatus(l.Status);
            if (toStage == null) {
                continue;
            }
            Stage_Event__c e = FunnelStages.liveEvent(FunnelStages.forLeadStatus(old.Status), toStage);
            e.Lead__c = l.Id;
            events.add(e);
        }
        if (!events.isEmpty()) {
            insert as system events;
        }
    }
}
