Ext.define('PHT.model.ProposalCode', {
    extend: 'Ext.data.Model',
    fields: [ 'id',
              'pcode',
             ],
    proxy: {
        type: 'ajax',
        url: 'options?mode=proposal_codes',
        reader: {
            type: 'json',
            root: 'proposal codes',
            successProperty: 'success'
        }
    }
});