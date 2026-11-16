/**
 * Funnel stage vocabulary shared by the Lead and Application handlers.
 * Stage values match Stage_Event__c.From_Stage__c and To_Stage__c.
 */
public with sharing class FunnelStages {

    public static final String SOURCE_LIVE = 'Live';
    public static final String LEAD_STATUS_APPLICATION_STARTED = 'Application Started';

    public static String forApplicationStatus(String status) {
        if (String.isBlank(status)) {
            return null;
        }
        return status == 'Draft' ? 'Applicant' : status;
    }

    public static String forLeadStatus(String status) {
        switch on status {
            when 'Open - Not Contacted' {
                return 'Inquiry';
            }
            when 'Working - Contacted' {
                return 'Contacted';
            }
            when 'Application Started' {
                return 'Application Started';
            }
            when 'Closed - Not Converted' {
                return 'Not Converted';
            }
            when else {
                return null;
            }
        }
    }

    public static Stage_Event__c liveEvent(String fromStage, String toStage) {
        return new Stage_Event__c(
            From_Stage__c = fromStage,
            To_Stage__c = toStage,
            Event_Date__c = System.now(),
            Source__c = SOURCE_LIVE
        );
    }
}
