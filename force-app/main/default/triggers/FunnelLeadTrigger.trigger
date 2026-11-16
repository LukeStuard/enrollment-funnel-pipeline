trigger FunnelLeadTrigger on Lead (after insert, after update) {
    if (Trigger.isInsert) {
        FunnelLeadHandler.handleAfterInsert(Trigger.new);
    } else {
        FunnelLeadHandler.handleAfterUpdate(Trigger.new, Trigger.oldMap);
    }
}
