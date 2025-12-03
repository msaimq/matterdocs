(function () {
    Office.onReady(function () {});

    // Command to show the MatterDocs taskpane.
    function showTaskPane(event) {
        Office.addin.showAsTaskpane().then(function () {
            event.completed();
        }).catch(function () {
            event.completed();
        });
    }

    // Expose for Office commands.
    if (typeof module !== "undefined") {
        module.exports = { showTaskPane: showTaskPane };
    }
    window.showTaskPane = showTaskPane;
})();
