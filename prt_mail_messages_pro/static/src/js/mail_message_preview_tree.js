/**********************************************************************************
* 
*    Copyright (C) Cetmix OÜ
*
*   Odoo Proprietary License v1.0
* 
*   This software and associated files (the "Software") may only be used (executed,
*   modified, executed after modifications) if you have purchased a valid license
*   from the authors, typically via Odoo Apps, or if you have received a written
*   agreement from the authors of the Software (see the COPYRIGHT file).
* 
*   You may develop Odoo modules that use the Software as a library (typically
*   by depending on it, importing it and using its resources), but without copying
*   any source code or material from the Software. You may distribute those
*   modules under the license of your choice, provided that this license is
*   compatible with the terms of the Odoo Proprietary License (For example:
*   LGPL, MIT, or proprietary licenses similar to this one).
* 
*   It is forbidden to publish, distribute, sublicense, or sell copies of the Software
*   or modified copies of the Software.
* 
*   The above copyright notice and this permission notice must be included in all
*   copies or substantial portions of the Software.
* 
*   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
*   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
*   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
*   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
*   DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
*   ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
*   DEALINGS IN THE SOFTWARE.
*
**********************************************************************************/

odoo.define("prt_mail_messages_pro.mail_message_preview_tree", function (require) {
    "use strict";

    var view_registry = require("web.view_registry");
    var ListView = require("web.ListView");
    var ListController = require("web.ListController");
    var ListRenderer = require("web.ListRenderer");
    var Widget = require("web.Widget");
    var ThreadWidget = require("im_livechat.legacy.mail.widget.Thread");
    const session = require("web.session");
    const {Component} = owl;
    const {ComponentWrapper} = require("web.OwlCompatibility");
    const {getMessagingComponent} = require("@mail/utils/messaging_component");
    const components = {
        ChatterContainer: getMessagingComponent("ChatterContainer"),
    };
    class ChatterContainerWrapperComponent extends ComponentWrapper {}

    var TreeRecordPreview = Widget.extend(ThreadWidget.prototype, {
        template: "TreeRecordPreview",
        render: function (thread, options, record) {
            this.renderElement();
        },
    });

    var MessagePreviewListController = ListController.extend({
        custom_events: _.extend({}, ListController.prototype.custom_events, {
            open_preview: "_onOpenPreview",
        }),
        init: function () {
            this._super.apply(this, arguments);
            // Preview mode by default
            this.renderer.previewMode = true;
            this.env = Component.env;
            this.models = this.env.services.messaging.modelManager.models;
            session.web_action = {};
            if (this.controlPanelProps && this.controlPanelProps.action.id) {
                session.web_action.action_id = this.controlPanelProps.action.id;
                this.message_action_id = this.controlPanelProps.action.id;
            }
        },
        start: function () {
            var self = this;
            var def1 = this._super.apply(this, arguments);

            const mailBus = self.env.bus;

            mailBus.on("delete_message", self, self._onDeleteMessage);
            mailBus.on("move_message", self, self._onMoveMessage);
            this.preview = new TreeRecordPreview(this);
            return this.alive(Promise.all([def1, this.preview.start()])).then(
                function () {
                    if (self.renderer.previewMode) {
                        self.renderPreview(self.$el);
                    }
                }
            );
        },
        is_action_enabled: function (action) {
            if (action === "preview") {
                return true;
            }
            return this._super(action);
        },
        renderElement: function () {
            this._super.apply(this, arguments);
            if (this.renderer.previewMode) {
                this.$el.find(".o_list_view").addClass("preview-mode");
            } else {
                this.$el.find(".o_list_view").removeClass("preview-mode");
                this.$el.find(".preview_row").removeClass("preview_row");
            }
        },
        renderButtons: function ($node) {
            this._super($node);
            if (!this.noLeaf && this.hasButtons) {
                // Create bootstrap tooltips
                this.$buttons.find(".o_cp_switch_preview").tooltip();
                if (this.renderer.previewMode) {
                    this.$buttons.find(".o_cp_switch_preview").addClass("active");
                }
                this.$buttons.on(
                    "click",
                    ".o_cp_switch_preview",
                    this._onSwitchPreview.bind(this)
                );
            }
        },
        renderPreview($node, record, thread, options) {
            options = options || {};
            this.preview.render(thread, options, record);
            $node.find(".o_list_view").addClass("preview-mode");
            this.preview.$el.appendTo($node.find(".o_list_view"));
        },
        _updateRendererState(state, params = {}) {
            var self = this;
            var res = this._super(state, params).then(function () {
                if (self.renderer.previewMode) {
                    self.renderPreview(self.$el);
                }
            });
            return res;
        },
        _onSwitchPreview: function (event) {
            event.stopPropagation();
            $(event.currentTarget).toggleClass("active");
            $(event.currentTarget).blur();
            this.renderer.switchPreviewMode();
            this.$(".tree-record-preview").empty();
            if (this.renderer.previewMode) {
                this.renderPreview(this.$el);
            } else {
                this.$el.find(".o_list_view").removeClass("preview-mode");
                this.$el.find(".preview_row").removeClass("preview_row");
            }
        },
        _onOpenPreview: function (event) {
            event.stopPropagation();
            var record_id = event.data.id;
            if (
                this.preview &&
                this.preview.record &&
                this.preview.record.id === record_id
            ) {
                return false;
            }
            // Remove exist preview
            this.$(".tree-record-preview").empty();
            // Get record
            var record = this.model.get(record_id, {raw: true});
            // Create new document thread
            // this.env.session.user_context.force_message_id = record.data.id;
            session.web_action.force_message_id = record.data.id;
            // This.env.session.user_context.force_message_model = record.data.model;
            session.web_action.force_message_model = record.data.model;
            if (this.message_action_id) {
                session.web_action.action_id = this.message_action_id;
                // This.context.action_id = this.message_action_id;
            }
            this._makeChatterContainerComponent(record);
            this._chatterContainerComponent.mount(this.$(".tree-record-preview")[0]);
            var message = this.models["mail.message"].find(
                (message) => message.id === record.data.id
            );

            if (message) {
                message.update({
                    _cx_display_document_link: true,
                });
            }
        },
        _makeChatterContainerComponent: function (record) {
            // From mail/static/src/widgets/form_renderer/form_renderer.js
            const props = {
                hasActivities: false,
                hasFollowers: false,
                hasMessageList: true,
                isAttachmentBoxVisibleInitially: false,
                previewMessageId: record.data.id,
                threadId: record.data.res_id,
                threadModel: record.data.model,
            };
            record.context.active_id = 166;
            this._chatterContainerComponent = new ChatterContainerWrapperComponent(
                this,
                components.ChatterContainer,
                props
            );
        },
        _onUpdateMessage: async function (message) {
            var self = this;
            await this.reload();
            if (!(this.preview && this.preview.record)) {
                // TODO: creating new TreeRecordPreview each time is not good,
                // TreeRecordPreview should be rewritten to new owl api
                this.preview = new TreeRecordPreview(this);
                this.preview.start().then(function () {
                    if (self.renderer.previewMode) {
                        self.renderPreview(self.$el);
                    }
                });
            } else if (
                this.preview &&
                this.preview.record &&
                this.preview.record.res_id === message.getID()
            ) {
                var params = {
                    messageIDs: [message.getID()],
                    name: message.getDocumentName(),
                    resID: message.getDocumentID(),
                    resModel: message.getDocumentModel(),
                };
                this.documentThread = this.call(
                    "mail_service",
                    "getOrAddDocumentThread",
                    params
                );
                var fetchDef = this.dp.add(this.documentThread.fetchMessages());
                return fetchDef.then(function (msg) {
                    // Render preview
                    if (!self.documentThread._messages.length) {
                        message = self.call(
                            "mail_service",
                            "getMessage",
                            self.documentThread._messageIDs[0]
                        );
                        self.documentThread.addMessage(message);
                    }
                    self.renderPreview(
                        self.$el,
                        self.preview.record,
                        self.documentThread
                    );
                });
            }
        },
        _onDeleteMessage: function () {
            var self = this;
            return this.reload().then(function () {
                if (self.preview) {
                    // Render empty preview
                    self.renderPreview(self.$el);
                }
            });
        },
        _onMoveMessage: function (message) {
            return this._onUpdateMessage(message);
        },
    });

    var MessagePreviewListRenderer = ListRenderer.extend({
        switchPreviewMode: function () {
            this.previewMode = !this.previewMode;
        },
        _onRowClicked: function (event) {
            this.$el.find(".preview_row").removeClass("preview_row");
            if (
                this.previewMode &&
                !$(event.target).parents(".o_list_record_selector").length
            ) {
                // Open preview
                var id = $(event.currentTarget).data("id");
                if (id) {
                    $(event.currentTarget).addClass("preview_row");
                    this.trigger_up("open_preview", {
                        id: id,
                        target: event.target,
                    });
                }
            } else {
                this._super(event);
            }
        },
    });

    var MessagePreviewListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: MessagePreviewListController,
            Renderer: MessagePreviewListRenderer,
        }),
    });

    view_registry.add("mail_message_preview_tree", MessagePreviewListView);

    return {
        MessagePreviewListController: MessagePreviewListController,
        MessagePreviewListView: MessagePreviewListView,
        MessagePreviewListRenderer: MessagePreviewListRenderer,
    };
});
