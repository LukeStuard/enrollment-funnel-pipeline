@IsTest
private class FunnelApplicationHandlerTest {

    @TestSetup
    static void setup() {
        FunnelTestData.account();
    }

    private static Id accountId() {
        return [SELECT Id FROM Account WHERE Name = :FunnelTestData.ACCOUNT_NAME WITH SYSTEM_MODE LIMIT 1].Id;
    }

    @IsTest
    static void convertsMatchingLeadIntoExistingContact() {
        Contact c = FunnelTestData.buildContact(accountId(), 'Match', 'match@example.com');
        FunnelTestData.insertAll(new List<SObject>{ c });
        Lead l = FunnelTestData.buildLead('Match', 'MATCH@example.com', 'Application Started');
        FunnelTestData.insertAll(new List<SObject>{ l });

        Test.startTest();
        FunnelTestData.insertAll(new List<SObject>{ FunnelTestData.buildApp(c.Id) });
        Test.stopTest();

        Lead after = [SELECT IsConverted, ConvertedContactId, ConvertedOpportunityId FROM Lead WHERE Id = :l.Id WITH SYSTEM_MODE];
        Assert.isTrue(after.IsConverted, 'Lead should convert on the first Application');
        Assert.areEqual(c.Id, after.ConvertedContactId, 'Lead should convert into the existing Contact');
        Assert.isNull(after.ConvertedOpportunityId, 'Conversion should not create an Opportunity');
    }

    @IsTest
    static void leavesLeadWithOtherStatusUnconverted() {
        Contact c = FunnelTestData.buildContact(accountId(), 'Working', 'working@example.com');
        FunnelTestData.insertAll(new List<SObject>{ c });
        Lead l = FunnelTestData.buildLead('Working', 'working@example.com', 'Working - Contacted');
        FunnelTestData.insertAll(new List<SObject>{ l });

        Test.startTest();
        FunnelTestData.insertAll(new List<SObject>{ FunnelTestData.buildApp(c.Id) });
        Test.stopTest();

        Assert.isFalse([SELECT IsConverted FROM Lead WHERE Id = :l.Id WITH SYSTEM_MODE].IsConverted, 'Only Application Started Leads convert');
    }

    @IsTest
    static void secondApplicationDoesNotConvert() {
        Contact c = FunnelTestData.buildContact(accountId(), 'Second', 'second@example.com');
        FunnelTestData.insertAll(new List<SObject>{ c });
        FunnelTestData.insertAll(new List<SObject>{ FunnelTestData.buildApp(c.Id) });
        Lead l = FunnelTestData.buildLead('Second', 'second@example.com', 'Application Started');
        FunnelTestData.insertAll(new List<SObject>{ l });

        Test.startTest();
        FunnelTestData.insertAll(new List<SObject>{ FunnelTestData.buildApp(c.Id) });
        Test.stopTest();

        Assert.isFalse([SELECT IsConverted FROM Lead WHERE Id = :l.Id WITH SYSTEM_MODE].IsConverted, 'Only the first Application converts');
    }

    @IsTest
    static void newApplicationLogsLiveApplicantEvent() {
        Contact c = FunnelTestData.buildContact(accountId(), 'Direct', 'direct@example.com');
        FunnelTestData.insertAll(new List<SObject>{ c });
        Application__c app = FunnelTestData.buildApp(c.Id);

        Test.startTest();
        FunnelTestData.insertAll(new List<SObject>{ app });
        Test.stopTest();

        List<Stage_Event__c> events = [
            SELECT From_Stage__c, To_Stage__c, Source__c, Contact__c
            FROM Stage_Event__c
            WHERE Application__c = :app.Id
            WITH SYSTEM_MODE
        ];
        Assert.areEqual(1, events.size(), 'One event for a new Application');
        Assert.isNull(events[0].From_Stage__c, 'First event has no from stage');
        Assert.areEqual('Applicant', events[0].To_Stage__c, 'Draft maps to Applicant');
        Assert.areEqual('Live', events[0].Source__c, 'Trigger events are Live');
        Assert.areEqual(c.Id, events[0].Contact__c, 'Event links the applicant');
    }

    @IsTest
    static void syntheticApplicationSkipsLiveEvent() {
        Contact c = FunnelTestData.buildContact(accountId(), 'Synthetic', 'synthetic@example.com');
        FunnelTestData.insertAll(new List<SObject>{ c });
        Application__c app = FunnelTestData.buildApp(c.Id);
        app.Synthetic_Key__c = 'TEST-APP-1';

        Test.startTest();
        FunnelTestData.insertAll(new List<SObject>{ app });
        Test.stopTest();

        Assert.areEqual(0, [SELECT COUNT() FROM Stage_Event__c WHERE Application__c = :app.Id WITH SYSTEM_MODE], 'Generator records carry their own history');
    }

    @IsTest
    static void statusChangeLogsLiveEvent() {
        Contact c = FunnelTestData.buildContact(accountId(), 'Moves', 'moves@example.com');
        FunnelTestData.insertAll(new List<SObject>{ c });
        Application__c app = FunnelTestData.buildApp(c.Id);
        FunnelTestData.insertAll(new List<SObject>{ app });

        Test.startTest();
        app.Status__c = 'Submitted';
        FunnelTestData.updateAll(new List<SObject>{ app });
        Test.stopTest();

        Stage_Event__c e = [
            SELECT From_Stage__c, To_Stage__c, Source__c
            FROM Stage_Event__c
            WHERE Application__c = :app.Id AND To_Stage__c = 'Submitted'
            WITH SYSTEM_MODE
        ];
        Assert.areEqual('Applicant', e.From_Stage__c, 'From stage is the previous status');
        Assert.areEqual('Live', e.Source__c, 'Trigger events are Live');
    }

    @IsTest
    static void bulkConversionSpansChunks() {
        Integer n = 150;
        Id acctId = accountId();
        List<Contact> contacts = new List<Contact>();
        List<Lead> leads = new List<Lead>();
        for (Integer i = 0; i < n; i++) {
            String email = 'bulk' + i + '@example.com';
            contacts.add(FunnelTestData.buildContact(acctId, 'Bulk' + i, email));
            leads.add(FunnelTestData.buildLead('Bulk' + i, email, 'Application Started'));
        }
        FunnelTestData.insertAll(contacts);
        FunnelTestData.insertAll(leads);

        List<Application__c> apps = new List<Application__c>();
        for (Contact c : contacts) {
            apps.add(FunnelTestData.buildApp(c.Id));
        }

        Test.startTest();
        FunnelTestData.insertAll(apps);
        Test.stopTest();

        Assert.areEqual(n, [SELECT COUNT() FROM Lead WHERE Id IN :leads AND IsConverted = true WITH SYSTEM_MODE], 'All Leads convert across chunks of 100');
    }
}
