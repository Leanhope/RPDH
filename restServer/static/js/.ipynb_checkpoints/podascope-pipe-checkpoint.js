$(document).ready(function() {

	poda = {};
	poda.pipeId = 'playground';

	poda.dom = {}
	poda.dom.pipe = document.querySelector('#poda-pipe');
	poda.dom.element = document.querySelector('#poda-element-full');
	poda.selected = null;
	poda.loading_spinner = document.querySelector('#poda-loading-icon');
	poda.options_collapsed = true;
	poda.fullPath = []
	// ---------------------------------------------------------------------------------------
	// Handlebars Templates

	poda.tmpl_element = Handlebars.compile(document.getElementById("poda-element-tmpl").innerHTML);
	poda.tmpl_element_full = Handlebars.compile(document.getElementById("poda-element-full-tmpl").innerHTML);
	poda.tmpl_term = Handlebars.compile(document.getElementById("poda-term-tmpl").innerHTML);

	Handlebars.registerPartial("poda-term-tmpl", document.getElementById("poda-term-tmpl").innerHTML);



	// ---------------------------------------------------------------------------------------
	// Handlebars Custom Helper

	Handlebars.registerHelper("greaterZero", function(count, options){
		if(count>0){return options.fn(this);} return options.inverse(this);
	});
	Handlebars.registerHelper("pipeIndex",function(eId, negate){ // allow negation for scope
		let n = negate ? -1 : 1;
		for(var i=0; i<poda.pipe.length;++i){
			if(eId==poda.pipe[i].eId){
				let v = poda.pipe.length-1-i;
				return v * n;
			}
		}
	});
	Handlebars.registerHelper("negScope",function(value){
		return value * -1;
	});
	Handlebars.registerHelper("sortedBy", function(sortBy, column, options){
		if(sortBy == column){return options.fn(this);} return options.inverse(this);
	});
	Handlebars.registerHelper("tabLabel", function(label, options){
		if(label != "/"){return options.fn(this);} return "Facets";
	});
	Handlebars.registerHelper("isNoRootFacet", function(parent_tId, options){
		if(parent_tId ===  0){return options.inverse(this);} return options.fn(this);
	});

	// NOTE: first element in visual representation is the last in the backend list
	Handlebars.registerHelper("isFirstElement", function(element, options){
		console.log("firstElementCheck");
		console.log("pipe length: " + poda.pipe.length);
		console.log("element index: " + element.elementindex);
		console.log(element);
		if (element.elementindex >= poda.pipe.length-1) { return options.fn(this); }
		return options.inverse(this);
	});
	Handlebars.registerHelper("isLastElement", function(element, options){
		if (element.elementindex == 0) { return options.fn(this); }
		return options.inverse(this);
	});
	Handlebars.registerHelper("notEmpty", function(listOrString, options){
		if (!listOrString) { return options.inverse(this); }
		if (listOrString.length > 0) { return options.fn(this); }
		return options.inverse(this);
	});
	Handlebars.registerHelper("equal", function(v1, v2, options){
		if (v1 === v2) { return options.fn(this); }
		return options.inverse(this);
	});
    

	// ---------------------------------------------------------------------------------------
	// Script Init

	poda.init = function() {

	// page events
	//NOTE: https://stackoverflow.com/questions/14677019/emulate-jquery-on-with-selector-in-pure-javascript
	$(".poda-reset-pipe").click(poda.resetPipe);

	// pipe-element events
    //$(poda.dom.pipe).on("click", ".poda-element", poda.selectPipeElement);
	$(poda.dom.pipe).on("click", ".poda-element", function()
	{console.log("Click Poda Element");
        poda.selectPipeElement});

	// full-page element OPTION events
	//$(poda.dom.element).on("click",".poda-remove-btn", poda.removePipeElement);
	//$(poda.dom.element).on("click",".poda-add-btn", poda.addRootElement);
	$(poda.dom.element).on("click",".poda-option-btn", function(event) {
		let el = $('#poda-element-options');
		el.on('shown.bs.collapse', function() { poda.options_collapsed = false; });
		el.on('hidden.bs.collapse', function() { poda.options_collapsed = true; });
		el.collapse('toggle'); // fire smooth collapse animation
	});
	//$(poda.dom.element).on("mousedown", ".poda-scope-spinner-input", poda.animateScope);
	//$(poda.dom.element).on("input change", ".poda-scope-spinner-input", poda.animateScope);
	//$(poda.dom.element).on("mouseup", ".poda-scope-spinner-input", poda.setScope);

	// search bar events
	$(poda.dom.element).on("keypress",".poda-search", function(event) { if(event.which==13){event.preventDefault(); poda.search(this);} } );
	$(poda.dom.element).on("focus",".poda-search", function() { this.selectionStart = this.selectionEnd = this.value.length; }); // set cursor at end of input text
	$(poda.dom.element).on("click", ".poda-previous-element", function() { poda.switchToOrCreateElement('next'); });
	$(poda.dom.element).on("click", ".poda-next-element", function() { poda.switchToOrCreateElement('previous'); });
	$(poda.dom.element).on("click", ".poda-element-path span:first-child", function() { poda.switchToRoot(); });

	// full-page element CONTENT events
	$(poda.dom.element).on("click", ".poda-term-label", function(event) {
        console.log("Click on Label", event.target.nodeName);
        event.stopImmediatePropagation();
        poda.selectTermLabel(event)});
	//$(poda.dom.element).on("click",".poda-more-btn", poda.loadMoreChildTerms);

	// sorting
	$(poda.dom.element).on("click","#poda-options-sortby .poda-option-clickable", function() {
		if (this.dataset && this.dataset.sortmode) { poda.sortTermsBy(this.dataset.sortmode); }
	});
	$(poda.dom.element).on("click","#poda-options-selection .poda-option-clickable", function() {
		if (this.dataset && this.dataset.selection) { poda.termSelection(this.dataset.selection); }
	});


	// for history
//	window.onpopstate = poda.history.popState;
}

	poda.init();

	// method to load initial pipe
	poda.loadPipe = async function() {

		console.log('window path: ' + window.location.pathname);

	 	if(window.location.pathname.includes('/pipes/')){
	 		poda.pipeId = window.location.pathname.split('/')[2];
	 		console.log(poda.pipeId);
	 	}

		poda.showLoadingIcon();
		//fetch('/pipes/'+poda.pipeId, {headers: {"Accept": "application/json"}})
		fetch('/returnRoot', {headers: {"Accept": "application/json"}})
		.then(response => response.json())
		.then(pipe => {

			//console.log("Pipe history length: " + pipe.historyLength);
			poda.preparePipe(pipe);
			poda.renderPipe();

			console.log('Assigning history id: ' + pipe.history_id);
			poda.history.id = pipe.history_id;
			poda.history.replaceState({'id': pipe.history_id});

			poda.prepareDragNDrop(); // prepare drag & drop functionality
			poda.hideLoadingIcon();
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	poda.resetPipe = function(event) {
		console.log("resetPipe");
		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId, {method:'PUT'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		event.preventDefault();
		return false;
	}



	// ---------------------------------------------------------------------------------------
	// Pipe Rendering

	// prepare pipe for rendering
	poda.preparePipe = function(pipe) {
		poda.pipe = pipe.elements;
		poda.selected = pipe.elements[pipe.selectedElement];
		poda.selected.elementindex = pipe.selectedElement;
	}

	// renders the whole pipe including the full page element
	poda.renderPipe = function(historyId=-1, focus_search_bar=false) {

		poda.setHistoryId(historyId);

		// clear current DOM contents
		let start = performance.now();
		poda.clearDOM(poda.dom.pipe);
		poda.clearDOM(poda.dom.element);
		console.log('Cleared DOM (took: ' + (performance.now() - start) + ' ms)');

		// map elements in reverse order
		console.log('Rendering ' + poda.pipe.length + ' pipe elements');
		poda.pipe.slice(0).reverse().map(element => poda.renderPipeElement(element));

		// ToDo: check which element is selected and if none, then select first
		if (poda.pipe && poda.pipe.length > 0) {
			console.log('Rendering selected element:');
			console.log(poda.selected);
			if (!poda.selected) { console.error("No element selected!") }
			else {
				poda.renderPipeElementFull(poda.selected, focus_search_bar);
				//let selectedDOM = poda.getPipeElementDOM(poda.selected.eId);
				//if (selectedDOM) { $(selecteDOM).addClass("poda-element-selected"); }
			}
		}
	}

	// clears the dom elements of this container
	//   see: https://coderwall.com/p/nygghw/don-t-use-innerhtml-to-empty-dom-elements
	//   and benchmark here: https://jsperf.com/innerhtml-vs-removechild/418
	poda.clearDOM = function(container) {
		for (let c = container.firstChild; c != null; c = container.firstChild) { container.removeChild(c); }
	}


	// renders the small pipe elements
	poda.renderPipeElement = function(element){

		//console.log(element);
		let html = createElementFromHtml(poda.tmpl_element(element));

		// this is the instance of the currently selected pipe element
		if (element == poda.selected) { html = poda.prepareSelected(element, html); }

		poda.dom.pipe.appendChild(html);
	}

	// renders the pull page pipe element
	poda.renderPipeElementFull = function(element, focus_search_bar=false){

		let html = createElementFromHtml(poda.tmpl_element_full(element));
		poda.dom.element.appendChild(html);

		// show/hide options panel accordingly
		//let optionsPanel = $('.poda-option-btn').parent().next();
		let optionsPanel = $('#poda-element-options');
		if (optionsPanel) {

			/*
			// below code uses the animations for collapsing
			if (poda.options_collapsed) { optionsPanel.collapse('hide'); }
			else { optionsPanel.collapse('show'); }
			*/

			// use below code to make the panel visible/hidden without animation
			if (poda.options_collapsed) { optionsPanel.removeClass('show'); }
			else { optionsPanel.addClass('show'); }
		}

		if (focus_search_bar) { $('.poda-search').focus(); }
	}


	// prepares the selected element and returns its modified html
	poda.prepareSelected = function(element, html) {

		//console.log("selected: " + element.eId);
		$(html).addClass('poda-element-selected');
		$(html).find('.arrow-box').addClass('arrow-box-selected');

		// color elements included by the scope accordingly
		let prevElement = $(poda.dom.pipe).children().last();
		poda.highlightScope(prevElement, element.scope);

		// store reference to element in DOM
		poda.selected.dom = html;
		return html;
	}

	/**
	 * Takes care of highlighting the scope of the selected pipe element.
	 * @param $prevElement : jQuery element
	 * @param resetAll : if true, resets elements out of the scope (all)
	 */
	poda.highlightScope = function($prevElement, scope, resetAll=false) {

		if (!$prevElement) { return; }

		//console.log("highlighting scope of " + scope);

		if (resetAll) {
			let i = 0;
			while ($prevElement.length > 0) {
				if (i < scope) {
					$prevElement.addClass('poda-in-scope');
					$prevElement.find('.arrow-box').addClass('arrow-box-in-scope');
				}
				else {
					$prevElement.removeClass('poda-in-scope');
					$prevElement.find('.arrow-box').removeClass('arrow-box-in-scope');
				}
				$prevElement = $prevElement.prev();
				i++;
			}
			return;
		}

		// highlight only elements within the scope
		for (var i = 0; i < scope; i++) {
			$prevElement.addClass('poda-in-scope');
			$prevElement.find('.arrow-box').addClass('arrow-box-in-scope');
			$prevElement = $prevElement.prev();
			if ($prevElement.length < 1) { break; }
		}
	}

	// ---------------------------------------------------------------------------------------
	// Pipe Element Helper Methods

	// adds a new root element after the currently selected one
	poda.addRootElement = async function(event) {

		console.log("Add root element");

		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/selected/add', {method:'PUT'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}


	// get the pipe element for the given element id
	poda.getPipeElement = function(eId) {
		for(var i in poda.pipe){
			if(poda.pipe[i].eId == eId){return [i,poda.pipe[i]];}
		}
		return [null,null];
	}

	// get the dom element for this element id
	poda.getPipeElementDOM = function(eId) {
		if (poda.dom.pipe == null) { return null; }
		let children = poda.dom.pipe.children;
		for (var c of children) {
			if (c.dataset.elementid === eId) { return c; }
		}
	}



	// ---------------------------------------------------------------------------------------
	// Interaction

	// removes the currently selected pipe element
	poda.removePipeElement = async function(event) {
		console.log("removePipeElement");
		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/selected/', {method:'DELETE'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id, true); poda.hideLoadingIcon(); })
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	// if user clicks on the "/", notifies server to replace facet with a root facet
	poda.switchToRoot = function() {
		console.log("switchToRoot");
		poda.showLoadingIcon();
		var el = poda.selected;
		fetch('/elements/'+ el.eId + '/path/move-up/', {'method': 'PUT'})
		//fetch('/returnRoot', {headers: {"Accept": "application/json"}})
		.then(response => response.json())
		.then(pipe => {
			poda.preparePipe(pipe);
			poda.renderPipe(pipe.history_id, true);
			poda.hideLoadingIcon();
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	// switch to another element from the currently selected one
	// (type is either previous or next)
	poda.switchToOrCreateElement = function(type) {
		console.log("switchToElement (" + type + ")");
		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/selected/switch-to/'+type, {'method': 'PUT'})
		.then(response => response.json())
		.then(pipe => {
			poda.preparePipe(pipe);
			poda.renderPipe(pipe.history_id, true);
			poda.hideLoadingIcon();
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	// after user pressed enter in search bar
	poda.search = function(domSearchBox) {
		console.log("search");
		let eId = poda.selected.eId;
		let query = domSearchBox.value;
		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/elements/'+eId+'/search/?query='+encodeURIComponent(query))
		.then(response => response.json())
		.then(pipe => {
			poda.preparePipe(pipe);
			poda.renderPipe(pipe.history_id, true);
			poda.hideLoadingIcon();
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	poda.setSearchBoxText = function(text) {
		poda.dom.element.querySelector(".poda-search").value = text;
	}

	// called when clicked on a term's label
	poda.selectTermLabel = function(event) {
		console.log("selectTermLabel");
		let el = poda.selected;
		let term =	event.target.dataset.tid
		console.log("TARGET: " + JSON.stringify(el))
		let leaf = true
		for(const x of el["terms"])
		{
			if(x["node"]["tId"] == term)
			{
				if(x["childCount"] > 0)
				{
					leaf = false
					poda.fullPath.push({"tID" : term, "label" : x["node"]["label"]})
				}
			}
		}
		//if(leaf == false){console.log('root term selection'); poda.updatePipeElementPath.call(this, event, term); return;}
		//poda.selectTerm(el.eId, term, "label");
		 poda.updatePipeElementPath.call(this, event, term)
	}

	poda.selectTerm = function(eId, tId, target) {
		console.log("selectTerm: eId="+eId+", tId="+tId+", target="+target);
		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/elements/'+eId+'/select/'+target, {method:'PUT', body:tId})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	// called when user clicked on a term selection option (optionType = "ALL", "CLEAR", "INVERT")
	// based on the currently shown terms list, the specified operation is performed
	poda.termSelection = function(operation) {
		let eId = poda.selected.eId;
		if (poda.selected.root) { alert("Operation not available for root elements!"); return; }
		console.log("termSelection: " + operation + "(eId=" + eId + ")");
		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/elements/'+eId+'/selection/'+operation, {method:'PUT'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	// when user clicks inside "Facets" (the root element) on a term, add it as a new facet
	poda.updatePipeElementPath = function(event, term) {
		// var el = poda.getEnclosingPipeElement(this);
		var el = poda.selected;
		console.log("updatePipeElementPath: eId=" + el.eId + ", tId=" + term);
		//poda.showLoadingIcon();
		fetch('/elements/' + el.eId + '/path/?tID='+term, {method:'PUT'})
		//fetch('/pipes/'+poda.pipeId+'/elements/'+el.eId+'/path/', {method:'PUT',body:this.dataset.tid})
		.then(response => response.json())
		.then(pipe => {
			poda.preparePipe(pipe);
			poda.renderPipe(pipe.history_id, true);
			poda.hideLoadingIcon();
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		event.preventDefault();
		return false;
	}


	// shows the element content if clicked on a pipe element
	poda.selectPipeElement = async function(event){

		let eId = this.dataset.elementid;
		if (poda.selected != null && eId == poda.selected.eId) { console.log("Already selected."); return; }
		console.log("Change selected element to: " + eId);

		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/selected/'+eId, {method:'PUT'})
		.then(response => response.json())
		.then(pipe => {
			poda.preparePipe(pipe);
			poda.renderPipe(pipe.history_id, true);
			poda.hideLoadingIcon();
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}


	// replaces the selected (full page) element and re-renders it
	poda.replaceSelectedElement = function(element, focus_search_bar=false) {

		// keep element index and DOM reference
		let selectedIndex = poda.selected.elementindex;
		element.elementindex = selectedIndex;
		element.dom = poda.selected.dom;

		// replace element in stored pipe
		poda.pipe[selectedIndex] = element;

		// remove current full-page element view and render new one
		//poda.dom.element.removeChild(poda.dom.element.firstChild);
		poda.clearDOM(poda.dom.element);
		poda.renderPipeElementFull(element, focus_search_bar);
	}


	// loads more child terms for the selected element
	poda.loadMoreChildTerms = function(event) {

		console.log('Load more terms...');
		let el = poda.selected;
		el.maxTerms *= 2;
		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/elements/'+el.eId+'/more?max='+encodeURIComponent(el.maxTerms))
		.then(response => response.json())
		.then(element => {
			poda.replaceSelectedElement(element);
			poda.hideLoadingIcon();
			//poda.setHistoryId(element.history_id); // do not store in history
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}


	// change sorting mode of selected element if clicked on upscore, downscore or label
	poda.sortTermsBy = function(sortBy) {

		console.log("sort terms by: " + sortBy);
		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/selected/sortby/'+sortBy, {method: 'PUT'})
		.then(response => response.json())
		.then(element => {
			poda.replaceSelectedElement(element);
			poda.hideLoadingIcon();
			poda.setHistoryId(element.history_id);
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}


	// animates the scope change
	poda.animateScope = function() {

		if (!poda.selected || !poda.selected.dom) { return; }
		let scope = Math.abs($('.poda-scope-spinner-input').val());
		$('.poda-scope-value').text(scope * -1); // update text of spinner
		poda.highlightScope($(poda.selected.dom).prev(), scope, true);
	}

	// set the scope for the selected element
	poda.setScope = function() {

		var scope = Math.abs(parseInt(this.value));
		var info = poda.pipe[poda.selected.elementindex];
		if (scope < 0) { scope = 0; }
		if (scope == info.scope) { return; }

		poda.showLoadingIcon();
		fetch('/pipes/'+poda.pipeId+'/elements/'+info.eId+'/scope/', {method:'PUT', body:scope})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}


	poda.showLoadingIcon = function(showOverlayAfterMs = 250) {

		// show "overlay" after waiting more than x milliseconds
		let showOverlay = showOverlayAfterMs >= 0 ? true : false;
		if (showOverlay) {
			poda.showOverlay = true;
			setTimeout(function() {
				if (!poda.showOverlay) { return; }
				let o = document.getElementById("overlay");
				if (o) { o.style.display = "block"; }
			}, showOverlayAfterMs);
		}
	}

	poda.hideLoadingIcon = function(update_history = true){

		// hide overlay if shown
		poda.showOverlay = false;
		let o = document.getElementById("overlay");
		if (o) { o.style.display = "none"; }
	}



	// ---------------------------------------------------------------------------------------
	// Drag & Drop Functionality

	// Prepare drag&drop functionality (drag and swap)
	poda.prepareDragNDrop = function() {

		console.log("Preparing drag & drop functionality");

		poda.dragndrop = {
			type: "drag", // current type
			allow_multiDrag: false, // enable/disable multidrag feature
			sortable: null,
			enable: function() { this.sortable.option("disabled", false); },
			disable: function() { this.sortable.option("disabled", true); },
			saveSortable: function() {
				console.log("Saving sortable store...");
				var order = this.sortable.toArray();
				console.log("Sortable order: " + order);
				localStorage.setItem(this.sortable.options.group.name, order.join('|'));
			},
			loadSortable: function() {
				console.log("Loading last sortable store...");
				var order = localStorage.getItem(this.sortable.options.group.name);
				var o = order ? order.split('|') : [];
				console.log("Sortable order: " + o);
				this.sortable.sort(o);
			}
		}

		// add event listener to drag button (double click will then change the dragndrop type)
		//$(poda.dom.pipe).on("dblclick", ".poda-drag-btn", function() { poda.changeDragNDropType(true); });

		// apply currently set type
		poda.applyDragNDropType();
	}

	// Changes the drag & drop to swap/drag elements.
	poda.changeDragNDropType = function(apply) {

		// destroy old functionality
		poda.dragndrop.sortable.destroy();
		let t = poda.dragndrop.type;
		if (t == "drag") { t = "swap"; }
		else if (t == "swap") { t = "drag"; }
		poda.dragndrop.type = t;
		console.log("Drag & drop type changed to: " + t);
		if (apply) { poda.applyDragNDropType(); }
	}

	// Apply the drag & drop type.
	poda.applyDragNDropType = function() {

		let n = null;
		let t = poda.dragndrop.type;
		let md = poda.dragndrop.allow_multiDrag;
		if (t == "drag") { n = poda.createSortable(false, md); }
		else if (t == "swap") { n = poda.createSortable(true, md); }
		poda.dragndrop.sortable = n;
	}

	// Creates a sortable instance.
	// @param useSwap - boolean to enable/disable swap
	poda.createSortable = function(useSwap = false, multiDrag = false) {

		// drag & drop functionality (requires "SortableJS" to be references previously)
		var sortable = Sortable.create(poda.dom.pipe, {
			delay: 50,
			animation: 200,
			swap: useSwap,
			multiDrag: multiDrag, // enable multidrag plugin
			selectedClass: "drag-selected", // css class for selected items
			swapClass: "swap-highlight", // css class for highlighting elements to swap
			handle: ".poda-draggable", // which part of the element is draggable
			draggable: ".poda-element", // the element that reprents an entry in the sortable
			//filter: "", // elements to exclude from drag
			preventOnFilter: false, // prevent default event on filtered elements
			onEnd: poda.dragEndEvent
		});

		// Problem:
		//   Even if our elements had different inputs in the search box,
		//   SortableJS generated the same ID for them, resulting in unstorable/sortable scenarios.
		//
		// Solution:
		//   Overwrite the generateId and toArray method so that they fit our needs.
		sortable._generateId = function(el) { return el.id.split(':')[1]; }
		sortable.toArray = function () {
			let order = [],
				el,
				children = this.el.children,
				options = this.options;

			for (var i = 0; i < children.length; i++) {
				el = children[i];
				if (this.closest(el, options.draggable, this.el, false)) {
					order.push(el.getAttribute(options.dataIdAttr) || this._generateId(el));
				}
			}
			return order;
		}
		return sortable;
	}

	// Called after user finished dragging a pipe element.
	poda.dragEndEvent = async function(evt) {

		// no change can be ignored
		if (evt.oldIndex == evt.newIndex) { return; }
		poda.showLoadingIcon();

		// dragged element
		let eId = evt.item.dataset.elementid;
		console.log("dragged element: " + eId);

		// the list was reversed so fix the index accordingly
		let i1 = poda.pipe.length - evt.oldIndex - 1;
		let i2 = poda.pipe.length - evt.newIndex - 1;

		// use endpoint according to drag & drop type
		let t = poda.dragndrop.type;
		let typeName = t.charAt(0).toUpperCase() + t.slice(1); // capitalize
		console.log(t + ': ' + i1 + ' => ' + i2);
		fetch('/pipes/' + poda.pipeId + "/elements/" + t + "?index1=" + i1 + "&index2=" + i2, { method: 'PUT' })
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id, true); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}



	// // ---------------------------------------------------------------------------------------
	// // History

	 poda.history = {

	 	id: -1,
	 	my_move: false,

	 	// requests current history from server
	 	getServerHistory: function(callback) {

	 		console.log("Retrieving history from server...");

	 		fetch('/pipes/' + poda.pipeId + "/history", { method: 'GET' })
	 		.then(response => response.json())
	 		.then(history => callback(history))
	 		.catch(reason => { console.error(reason.message); } );
	 	},

	 	// set variable to true to ignore/avoid callback execution
	 	move: function(steps = 1, ignore_event = true) {
	 		if (ignore_event) { poda.history.my_move = true; }
	 		window.history.go(steps);
	 	},

	 	replaceState: function(obj) {
	 		window.history.replaceState(obj, "poda", document.URL);
	 	},

	 	pushState: function(obj) {
	 		window.history.pushState(obj, "poda", document.URL);
	 		console.log('[HISTORY] push:');
	 		console.log(obj);
		},

	 	popState: function(event) {

	 		// ignore own "back" call
	 		if (this.my_move) { this.my_move = false; return; }
			console.log('[History] popState event');
	 		// user may have moved from another page back to "ours"
	 		let state = window.history.state;
	 		if (!state || !('id' in state)) {
	 			console.warn("Missing history information!");
	 			if (poda.history.id >= 0) {
	 				console.log('Replacing history with id: ' + poda.history.id);
	 				poda.history.replaceState({'id': poda.history.id});
	 				poda.history.popState(event);
	 			}
	 			else { poda.history.move(-1); }
	 			return;
	 		}

			// load pipe with current history id
	 		let hId = window.history.state.id
	 		poda.history.id = hId;
	 		console.log('Loading pipe from history (id: ' + hId + ')');

	 		poda.showLoadingIcon(100); // show overlay quickly
	 		fetch('/pipes/'+poda.pipeId+'/history/'+hId, {method: 'PUT', headers: {"Accept": "application/json"}})
	 		.then(response => response.json())
	 		.then(pipe => {
	 			if (pipe.failure != '') { throw new Error(pipe.failure); }
	 			poda.preparePipe(pipe); poda.renderPipe(); poda.hideLoadingIcon();
	 			console.log('Pipe successfully loaded from history. (hId: ' + hId + ')');
	 		})
	 		.catch(reason => {
	 			poda.hideLoadingIcon();
	 			let msg = 'Failed to load pipe from history! (' + reason.message + ')';
	 			console.error(msg + " (hId: " + hId + ')');
	 			alert(msg);
	 		});
	 	}

	}; // end poda.history

	// // set history Id (if greater 0) and push state to local history API
	 // @param pushIfEqual - push the state even if the id is the same?
	 poda.setHistoryId = function(historyId=-1, pushIfEqual=false) {
	 	if (pushIfEqual && poda.history.id === historyId) { return; }
	 	if (historyId >= 0) {
	 		poda.history.id = historyId;
	 		poda.history.pushState({'id': historyId});
	 	}
	 }


	/*Start App*/
	poda.init();
	poda.loadPipe();

});


function createElementFromHtml(html) {

	var result = document.createElement('div');
	result.innerHTML = html.trim();
	return result.firstElementChild;
}
