@IsTest
private class FunnelLeadHandlerTest {

    @IsTest
    static void newLeadLogsInquiry() {
        Lead l = FunnelTestData.buildLead('Inquiry', 'inquiry@example.com', 'Open - Not Contacted');

        Test.startTest();
        FunnelTestData.insertAll(new List<SObject>{ l });
        Test.stopTest();

        Stage_Event__c e = [SELECT From_Stage__c, To_Stage__c, Source__c FROM Stage_Event__c WHERE Lead__c = :l.Id WITH SYSTEM_MODE];
        Assert.isNull(e.From_Stage__c, 'First event has no from stage');
        Assert.areEqual('Inquiry', e.To_Stage__c, 'Open Lead maps to Inquiry');
        Assert.areEqual('Live', e.Source__c, 'Trigger events are Live');
    }

    @IsTest
    static void statusChangeLogsEvent() {
        Lead l = FunnelTestData.buildLead('Contacted', 'contacted@example.com', 'Open - Not Contacted');
        FunnelTestData.insertAll(new List<SObject>{ l });

        Test.startTest();
        l.Status = 'Working - Contacted';
        FunnelTestData.updateAll(new List<SObject>{ l });
        Test.stopTest();

        Stage_Event__c e = [SELECT From_Stage__c FROM Stage_Event__c WHERE Lead__c = :l.Id AND To_Stage__c = 'Contacted' WITH SYSTEM_MODE];
        Assert.areEqual('Inquiry', e.From_Stage__c, 'From stage is the previous status');
    }

    @IsTest
    static void syntheticLeadSkipsInsertEvent() {
        Lead l = FunnelTestData.buildLead('Synthetic', 'synthetic.lead@example.com', 'Open - Not Contacted');
        l.Synthetic_Key__c = 'TEST-LEAD-1';

        Test.startTest();
        FunnelTestData.insertAll(new List<SObject>{ l });
        Test.stopTest();

        Assert.areEqual(0, [SELECT COUNT() FROM Stage_Event__c WHERE Lead__c = :l.Id WITH SYSTEM_MODE], 'Generator records carry their own history');
    }

    @IsTest
    static void conversionDoesNotLogLeadEvent() {
        Account a = FunnelTestData.account();
        Contact c = FunnelTestData.buildContact(a.Id, 'Converts', 'converts@example.com');
        FunnelTestData.insertAll(new List<SObject>{ c });
        Lead l = FunnelTestData.buildLead('Converts', 'converts@example.com', 'Application Started');
        FunnelTestData.insertAll(new List<SObject>{ l });

        Test.startTest();
        FunnelTestData.insertAll(new List<SObject>{ FunnelTestData.buildApp(c.Id) });
        Test.stopTest();

        Assert.isTrue([SELECT IsConverted FROM Lead WHERE Id = :l.Id WITH SYSTEM_MODE].IsConverted, 'Lead converts');
        Assert.areEqual(1, [SELECT COUNT() FROM Stage_Event__c WHERE Lead__c = :l.Id WITH SYSTEM_MODE], 'Only the insert event; conversion is logged on the Application side');
    }
}
