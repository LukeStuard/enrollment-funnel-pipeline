trigger FunnelApplicationTrigger on Application__c (after insert, after update) {
    if (Trigger.isInsert) {
        FunnelApplicationHandler.handleAfterInsert(Trigger.new);
    } else {
        FunnelApplicationHandler.handleAfterUpdate(Trigger.new, Trigger.oldMap);
    }
}
