Ext.define('PHT.model.SessionName', {
    extend: 'Ext.data.Model',
    fields: [ 'id',
              'session',
              'handle',
             ],
    proxy: {
        type: 'ajax',
        url: '/pht/options?mode=session_names',
        timeout: 300000,
        reader: {
            type: 'json',
            root: 'session names',
            successProperty: 'success'
        }
    }
});
