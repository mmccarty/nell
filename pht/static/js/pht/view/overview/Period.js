Ext.define('PHT.view.overview.Period', {
    extend: 'Ext.draw.Sprite',
    alias: 'widget.overviewperiod',
    constructor: function() {
        this.px2time = Ext.create('PHT.view.overview.PixelsToTime');
        this.day     = 0;
        this.color   = 'red';
        var parentConfig = {
            type: 'rect',
            fill: 'red',
            stroke: 2,
            width: 45,
            height: this.px2time.dayPx,
            opacity: .6,
            x: 100,
            y: this.vertOffset,
            floating: true,
        };

        var me = this;
        this.listeners = {
            click: function() {
                console.log('click');
            },
            mouseover: function(e, t) {
                //console.log('mouseover');
                console.log(e);
                console.log(t);
                me.tooltip.showAt([me.x, me.y]);
            },
            mouseout: function() {
                //console.log('mouseout');
                me.tooltip.hide();
            },
        };

        this.callParent([parentConfig]);
    },

    setDrawComponent: function(drawComponent){
        this.drawComponent = drawComponent;
        this.drawComponent.items.push(this);
    },

    setData: function(record){
        this.record = record;
        if (this.sibling) {
            this.sibling.setData(record);
        }

        if (this.record.get('session').type == 'elective'){
            this.setColor('purple');
        } else if (this.record.get('session').type == 'fixed'){
            this.setColor('red');
        } else if (this.record.get('session').type == 'windowed'){
            if (this.record.get('session').guaranteed) {
                this.setColor('green');
            } else {
                this.setColor('yellow');
            }
        } else if (this.record.get('session').type == 'open'){
            this.setColor('blue');
        }
        if (this.record.get('session').science == 'maintenance'){
            this.setColor('orange');
        }

        var id = 'dss_' + record.get('id');
        this.setAttributes({id : id })
        this.tooltip = Ext.create('Ext.tip.ToolTip', {
            target: id,
            html: record.get('handle'),
        });

    },

    setColor: function(color) {
        this.color = color;
        this.setAttributes({fill: color});
    },

    setDay: function(day) {
        this.day = day;
        this.y   = this.px2time.day2px(day);
        this.setAttributes({y: this.y});
    },

    setTime: function(start, duration) {
        var endTime = start + duration;
        if (endTime > 24) {
            duration_prime = endTime - 24;
            duration       = duration - duration_prime;
            this.createSibling(this.day + 1, 0, duration_prime);
        }

        this.x     = this.px2time.time2px(start),
        this.width = this.px2time.duration2px(duration);
        
        this.setAttributes({x : this.x, width : this.width});
    },

    createSibling: function(day, start, duration){
        this.sibling = Ext.create('PHT.view.overview.Period');
        this.sibling.setDrawComponent(this.drawComponent);
        this.sibling.setDay(day);
        this.sibling.setTime(start, duration);
    }

});
