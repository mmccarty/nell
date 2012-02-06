Ext.define('PHT.store.PrimaryInvestigators', {
    extend: 'Ext.data.Store',
    model: 'PHT.model.PrimaryInvestigator',
    autoLoad: true,
    proxy: {
        type: 'ajax',
        url: '/pht/proposal/pis',
        reader: {
            type: 'json',
            root: 'pis',
            successProperty: 'success'
        }
    }
});
