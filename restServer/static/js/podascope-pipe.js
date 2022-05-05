
$(document).ready(function() {

	poda = {};
	poda.pipeId = 'playground';

	poda.dom = {}
	poda.dom.pipe = document.querySelector('#poda-pipe');
	poda.dom.element = document.querySelector('#poda-element-full');
	poda.dom.pipeCollection = document.querySelector('#collapseQueries')
	poda.dom.queryList = document.querySelector('#queryList')
	//poda.dom.selectQueries = document.querySelector('#poda-stored-queries')
	poda.selected = null;
	poda.loading_spinner = document.querySelector('#poda-loading-icon');
	poda.options_collapsed = true;
	poda.selectedSpan = null
	poda.editMode = false
	poda.selectedRange = []
	poda.selectedSpan = null
	poda.spansToAdd = []
	poda.pipeCollection = null
	poda.selectedPipe = 0
	// ---------------------------------------------------------------------------------------
	// Handlebars Templates
	poda.tmpl_pipe = Handlebars.compile(document.getElementById("poda-pipe-tmpl").innerHTML);
	poda.tmpl_element = Handlebars.compile(document.getElementById("poda-element-tmpl").innerHTML);
	poda.tmpl_element_full = Handlebars.compile(document.getElementById("poda-element-full-tmpl").innerHTML);
	poda.tmpl_term = Handlebars.compile(document.getElementById("poda-term-tmpl").innerHTML);
	poda.tmpl_queryList = Handlebars.compile(document.getElementById("queryList-tmpl").innerHTML)
	poda.tmpl_queryButton = Handlebars.compile(document.getElementById("queryButton-tmpl").innerHTML)
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

	Handlebars.registerHelper("hasNoTerms",function(){
		if(poda.selected.termCount == 0)
			return true;
		else
			return false;
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
		if(element.eId == 0)
			return options.fn(this)
		else
			return options.inverse(this)
	});

	Handlebars.registerHelper("isSecondElement", function(element, options){
		if(element.eId == 1)
			return options.fn(this)
		else
			return options.inverse(this)
	});

	Handlebars.registerHelper("isRegularElement", function(element, options){
		if(element.eId > 1)
			return options.fn(this)
		else
			return options.inverse(this)
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

	
	$(poda.dom.pipeCollection).on("click", ".poda-element", function(event)
	{console.log("Click Poda Element");
		console.log(event)
		//event.stopImmediatePropagation()
        poda.selectPipeElement(event)
	});

	// full-page element OPTION events
	$(document).on("click",".poda-remove-btn", function(event)
	{
		event.stopImmediatePropagation();
		poda.removePipeElement(event)
	});
	$(document).on("click",".poda-add-btn", function(event)
	{
		event.stopImmediatePropagation();
		poda.addRootElement(event)
	});

	$(document).on("click",".poda-add-pipe", function(event)
	{
		event.stopImmediatePropagation();
		poda.showLoadingIcon()
		fetch("/addPipe/", {method: "PUT"})
			.then(response => response.json())
			.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
			.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		  
	});

	$(document).on("click",".poda-rmvPipe-btn", function(event)
	{
		event.stopImmediatePropagation();
		poda.deletePipe(event)
	});
	$(document).on("click",".poda-save-btn", function(event)
	{
		event.stopImmediatePropagation();
		poda.storeQuery()
	});
	$(queryList).on("click", ".queryButton", function(event)
	{
		event.stopImmediatePropagation();
		poda.showLoadingIcon()
		 fetch("/setToPipe/?pID=" + event.target.attributes["pipeid"].value, {method: "PUT"})
		 	.then(response => response.json())
		 	.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		 	.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	});

	// $(poda.dom.selectQueries).on("click",".clearQueries", function(event)
	// {
	// 	console.log("hi")

	// 	event.stopImmediatePropagation();
	// 	poda.clearQueries()
	// });

	// $(poda.dom.selectQueries).on("click",".setQuery", function(event)
	// {
	// 	event.stopImmediatePropagation();
	// 	poda.setQuery(event)
	// });

	$(poda.dom.element).on("click",".addFacet", async function(event)
	{
		event.stopImmediatePropagation();
		console.log(poda.selected)

		var termName = prompt("Please enter the name of facet to add under \"" + poda.selected.element.label + "\".");
		console.log("HIER", termName)
		if (termName != "" && termName != null) {
			poda.showLoadingIcon();
			await fetch("/addTerm/?label=" + termName + "&parentID=" + poda.selected.element.tId, {
				method: "PUT"})
				.then(response => response.json())
				.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
				.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
  			}
		poda.editMode = false
	});

	$(poda.dom.element).on("click","#setWiki", function(event)
	{
		event.stopImmediatePropagation();
		console.log(poda.selected.element)

		var id = prompt("Please enter the ID of the Wikipedia page to link to this term.");
		if (id != "" && id != null) {
			fetch("/setWikiID/?wikiID=" + id + "&termID=" + poda.selected.element.tId, {
				method: "PUT"});
  			}
		poda.refreshElement();
		poda.editMode = false
	});



	$(poda.dom.element).on("click",".poda-edit-mode", function(event)
	{
		event.stopImmediatePropagation();
		var switchEl = document.getElementById("editSwitch")


		if(document.getElementById("editMode").hidden == true)
		{
			switchEl.classList.add("fa-search")
			switchEl.classList.remove("fa-edit")
			document.getElementById("editMode").hidden = false
			poda.editMode = true
			boxes = document.getElementsByClassName("checkboxes")
			for(const i of boxes)
			{
				i.hidden=false
			}

		}
		else
		{
			switchEl.classList.add("fa-edit")
			switchEl.classList.remove("fa-search")
			document.getElementById("editMode").hidden = true
			boxes = document.getElementsByClassName("checkboxes")
			for(const i of boxes)
			{
				i.hidden=true
			}
			poda.editMode = false
		}
		console.log(poda.editMode)

	});


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
	$(poda.dom.element).on("click", ".rankingSelect", function(event) {
		event.stopImmediatePropagation()
		poda.showLoadingIcon();
		fetch('/toggleRanking/', {method:'PUT'})
		.then(response => response.json())
		.then(pipe => {
		poda.preparePipe(pipe);
		poda.renderPipe(pipe.history_id, true);
		poda.hideLoadingIcon();})
	})
	$(poda.dom.element).on("keypress",".poda-search", function(event) { if(event.which==13){event.preventDefault(); event.stopImmediatePropagation() ;poda.search(this);} } );
	$(poda.dom.element).on("click", ".searchButton", function(event){event.stopImmediatePropagation(); poda.search($('#searchBar')[0])})
	$(poda.dom.element).on("focus",".poda-search", function() { this.selectionStart = this.selectionEnd = this.value.length; }); // set cursor at end of input text
	$(poda.dom.element).on("click", ".poda-previous-element", function() { poda.switchToOrCreateElement('next'); });
	$(poda.dom.element).on("click", ".poda-next-element", function() { poda.switchToOrCreateElement('previous'); });
	$(poda.dom.element).on("click", ".poda-element-path span:first-child", function(event) { 
		event.stopImmediatePropagation();
		if(!poda.editMode)
		{
			poda.switchToRoot(); 
		}});
	$(poda.dom.element).on("click", ".input-group-text", function(event) {
		event.stopImmediatePropagation();
		if(!poda.editMode)
		{
		poda.switchInPath(this);
	 } });
	
	$(poda.dom.element).on("click", ".poda-delete-terms", function(event) { 
		event.stopImmediatePropagation();
		poda.deleteTerms(); });

	$(poda.dom.element).on("change", ".form-range", function(event) { 
		event.stopImmediatePropagation();
		poda.updateContext(this.value); });
	

	// full-page element CONTENT events
	$(poda.dom.element).on("click", ".poda-term-label", function(event) {
        //console.log("Click on Label", event.target.nodeName);
        event.stopImmediatePropagation();
        poda.selectTermLabel(event)});

	$(poda.dom.element).on("click", ".goDeeper", function(event)
	{
		event.stopImmediatePropagation();
		console.log(event.target)

		if(event.target.classList.contains("goDeeper"))
		{
			if(!poda.editMode)
			{
				termID = event.target.attributes["termid"].value
				poda.updatePipeElementPath.call(this, event, termID)
				return
			}
		}
	})

	$(poda.dom.element).on("click",".poda-more-btn", function(event) 
	{
        event.stopImmediatePropagation();
		poda.loadMoreChildTerms(event)});

	// sorting
	$(poda.dom.element).on("click","#poda-options-sortby .poda-option-clickable", function(event) {
        event.stopImmediatePropagation();
		if (this.dataset && this.dataset.sortmode) { poda.sortTermsBy(this.dataset.sortmode); }
	});
	$(poda.dom.element).on("click","#poda-options-selection .poda-option-clickable", function(event) {
		if (this.dataset && this.dataset.selection) { 
			event.stopImmediatePropagation();
			poda.termSelection(this.dataset.selection); }
	});

	$(poda.dom.element).on("click","#deletedSelector", function(event) {
		 {  event.stopImmediatePropagation();
			 poda.deletedTerms()}
	});

	$(poda.dom.element).on("click", ".poda-restore-terms", function(event) { 
		event.stopImmediatePropagation();
		poda.restoreTerms(); });	
		

	$(poda.dom.element).on("click", ".confirmAll", function(event) { 

		event.stopImmediatePropagation();

		poda.showLoadingIcon()

		let qString = "/addSpans/?"
	
		for(const i of poda.spansToAdd)
		{
	
			qString += "spans=" + i + "&"
		}
		qString = qString.slice(0, -1)

		fetch(qString, {method: "PUT"})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		event.preventDefault();

		poda.spansToAdd = []
		poda.editMode = false
		
		//poda.refreshElement();
		});	

	
	$(poda.dom.element).on("click", ".addSpan", function(event) { 
		event.stopImmediatePropagation();
		form = document.getElementById("termList")
		target = form[form.value]
		range = poda.selectedRange
		spanElement = poda.selectedSpan.offsetParent

		console.log(target, range, spanElement)
		console.log(spanElement.attributes["startChar"])

		poda.selectedSpan.offsetParent.innerHTML = poda.selectedSpan.offsetParent.innerHTML + 
		"</br> Adding: \"" + poda.selectedSpan.offsetParent.innerText.substring(
			range[0]-spanElement.attributes["startChar"].value, range[1]-spanElement.attributes["startChar"].value + 1)
			+"\" as \"" + target.attributes["parent"].value + "/" + target.attributes["term"].value + "\""
			
		let term = parseInt(spanElement.attributes["data-tid"].value)
		console.log(term)
		poda.spansToAdd.push(... [term], parseInt(target.attributes["termid"].value), range[0], range[1])
		return
	});	

	
	$(poda.dom.element).on("click","#findSpans", async function(event)
	{
		event.stopImmediatePropagation();
		console.log(poda.selected.element)

		var query = prompt("Please enter the string whose occurences should be added to the current facet. This could take a while. Note that entered term is treated as a regular expression, so it is case-sensitive by default.");
		poda.showLoadingIcon();
		if (query != "" && query != null) {
			await fetch("/findSpans/?query=" + query + "&tID=" + poda.selected.element.tId, {
				method: "PUT"})
				.then(response => response.json())
				.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
				.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
  			}
		poda.editMode = false;
		poda.refreshElement();
		//poda.hideLoadingIcon();

	});

	$(poda.dom.element).on("click","#searchCase", async function(event)
	{
		event.stopImmediatePropagation();

		poda.showLoadingIcon();
		fetch("/flipCase/" ,{method: "PUT"})
			.then(response => response.json())
			.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
			.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		poda.editMode = false;
	});


	$(poda.dom.element).on("click", "#wikiToggle", function(event) 
	{
		event.stopImmediatePropagation();
		console.log(document.getElementById("wikiRef"))
		if(document.getElementById("wikiRef").hidden == true)
			document.getElementById("wikiRef").hidden = false
		else
			document.getElementById("wikiRef").hidden = true
	});

	$(document).on("click", ".resetChanges", function(event) 
	{
		event.stopImmediatePropagation();
		poda.showLoadingIcon();
		fetch('http://141.54.138.235:8000/resetChanges', {'method': 'PUT'})
		.then(response => response.json())
		.then(pipe => {
			poda.preparePipe(pipe);
			poda.renderPipe(pipe.history_id, true);
			poda.hideLoadingIcon();
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	});


	}
	
poda.updateContext = function(context)
{
	poda.showLoadingIcon()
	fetch("/changeContext/?context=" + context, {
		method: "PUT"})
		.then(response => response.json())
		.then(element => {
			poda.replaceSelectedElement(element);
			poda.hideLoadingIcon();
			//poda.setHistoryId(element.history_id); // do not store in history
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
}
	
poda.deletedTerms = function()
{
	poda.showLoadingIcon()
	fetch("/toggleDeleted/", {method: "PUT"})
	.then(response => response.json())
	.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
	.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
}

poda.deleteTerms = function()
{
	var el = poda.selected;
	console.log(poda.selected.path)
	poda.showLoadingIcon()
	let qString = "/hideTerms?eid=" + JSON.stringify(el.eId) + "&";

	let x = document.getElementsByClassName("poda-term-label");

	for(const i of x)
	{
		if(i.childNodes[1].checked)
		{
			console.log(i)
			qString += "terms=" + (i.dataset["tid"]) + "&"
		}
	}
	qString = qString.slice(0, -1)

	fetch(qString, {method: "PUT"})
	.then(response => response.json())
	.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
	.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	poda.editMode = false
}

poda.restoreTerms = function()
{
	var el = poda.selected;
	poda.showLoadingIcon()

	let qString = "/restoreTerms?eid=" + JSON.stringify(el.eId) + "&";
	let x = document.getElementsByClassName("poda-term-label");

	for(const i of x)
	{
		if(i.childNodes[1].checked)
		{
			console.log(i)
			qString += "terms=" + (i.dataset["tid"]) + "&"
		}
	}
	qString = qString.slice(0, -1)

	fetch(qString, {method: "PUT"})
	.then(response => response.json())
	.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
	.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	poda.editMode = false
}

poda.switchInPath = function(input) {
	console.log("SWITCH IN PATH")
	console.log(poda.selected)
	var el = poda.selected.eId;
	console.log(input)
	
	
	if(input.innerText != "/")
	{
		var target;
		for(i in poda.pipe[el].path)
		{
			if(poda.pipe[el].path[i]["label"] == input.innerText)
			{
				target = poda.pipe[el].path[i]["tID"]
				poda.updatePipeElementPath.call(this, event, target, poda.pipe[el].path[i]["isSpan"])
				console.log(poda.selected.path)

				break;
			}
		}
		
	}
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

	poda.deletePipe = function(event) {
		console.log("deletePipe");
		poda.showLoadingIcon();
		pipeID = event.target.parentElement.parentElement.attributes["pipe-id"].value
		fetch('/deletePipe/?pID=' + pipeID, {method:'PUT'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		event.preventDefault();
		poda.editMode = false
		return false;
	}

	poda.storeQuery = function() {
		console.log("storeQuery");
		poda.showLoadingIcon();
		fetch('/storeQuery/', {method:'PUT'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		event.preventDefault();
		return false;
	}

	poda.clearQueries = function() {
		console.log("clearQueries");
		poda.showLoadingIcon();
		fetch('/clearQueries/', {method:'PUT'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		event.preventDefault();
		return false;
	}
	poda.setQuery = function(event){
		query = event.delegateTarget.children[0].children[0].value
		poda.showLoadingIcon();
		fetch('/setQuery/?query='+query, {method:'PUT'})
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
		poda.pipeCollection = pipe
		poda.selectedPipe = pipe.selectedPipe
		poda.pipe = pipe.pipes[poda.selectedPipe].elements;

		poda.selected = pipe.pipes[poda.selectedPipe].elements[pipe.pipes[poda.selectedPipe].selectedElement];
		poda.selected.elementindex = pipe.pipes[poda.selectedPipe].selectedElement;
	}

	// renders the whole pipe including the full page element
	poda.renderPipe = function(historyId=-1, focus_search_bar=false) {

		poda.setHistoryId(historyId);

		// clear current DOM contents
		let start = performance.now();
		poda.clearDOM(poda.dom.pipe);
		poda.clearDOM(poda.dom.element);		
		poda.clearDOM(poda.dom.pipeCollection);
		poda.clearDOM(poda.dom.queryList);


		console.log('Cleared DOM (took: ' + (performance.now() - start) + ' ms)');
		console.log('Rendering ' + poda.pipe.length + ' pipe elements');

		for(let i = 0; i < poda.pipeCollection.pipes.length; i++)
		{	
			poda.renderSinglePipe(poda.pipeCollection.pipes[i]);
		}
		poda.dom.pipeCollection.innerHTML += '<span title ="Add a new Query" style="margin-left: 30px; margin-bottom:50px;" class ="poda-add-pipe"><i class="fas fa-plus fa-2x poda-clickable" ></i></span>'
		//poda.pipe.map(element => poda.renderPipeElement(element));

		// ToDo: check which element is selected and if none, then select first
		if (poda.pipe && poda.pipe.length > 0) {
			console.log('Rendering selected element:');
			console.log(poda.selected);
			if (!poda.selected) { console.error("No element selected!") }
			else {
				poda.renderPipeElementFull(poda.selected, focus_search_bar);
				}
		}
		console.log("ELEMENT:")
		console.log(poda.selected)
		if(poda.pipeCollection.pipes[poda.selectedPipe].selectedElement > 0)
		{
			let html = createElementFromHtml(poda.tmpl_queryList(null));
			poda.dom.queryList.appendChild(html);
			for(let i = 0; i < poda.pipeCollection.pipes.length; i++)
			{	
				if(i != poda.selectedPipe)
				{
					if(poda.selected.tId == 0)
					{
						let html = createElementFromHtml(poda.tmpl_queryButton(poda.pipeCollection.pipes[i]))
						console.log(poda.selected.selectedPipe)
						if(i == poda.selected.selectedPipe)
						{
							console.log(poda.selected.selectedPipe)
							console.log(html.classList)
							html.classList.remove('btn-info');
							console.log(html.classList)

							html.classList.add('btn-success');
						}
						poda.dom.queryList.children[0].children[1].appendChild(html)		
					}
				}
			}
		}
	}

	// clears the dom elements of this container
	//   see: https://coderwall.com/p/nygghw/don-t-use-innerhtml-to-empty-dom-elements
	//   and benchmark here: https://jsperf.com/innerhtml-vs-removechild/418
	poda.clearDOM = function(container) {
		for (let c = container.firstChild; c != null; c = container.firstChild) { container.removeChild(c); }
	}

	poda.renderSinglePipe = function(pipe){
		var str = ""
		for(let i = 0; i< pipe.elements.length; i++) {
			var elHtml = createElementFromHtml(poda.tmpl_element(pipe.elements[i]));
			if(pipe.pid == poda.selectedPipe)
				if (pipe.elements[i] == poda.selected) 
					elHtml = poda.prepareSelected(pipe.elements[i], elHtml); 

			str += elHtml.innerHTML
		}

		let pipeHtml = createElementFromHtml(poda.tmpl_pipe(pipe));
		pipeHtml.querySelector("#innerPipe").innerHTML = str
		console.log(pipeHtml)
		//pipeHtml.innerHTML = str
		poda.dom.pipeCollection.appendChild(pipeHtml);
	}


	// renders the small pipe elements
	poda.renderPipeElement = function(element){
		let html = createElementFromHtml(poda.tmpl_element(element));
		// this is the instance of the currently selected pipe element
		if (element == poda.selected) { html = poda.prepareSelected(element, html); }

		poda.dom.pipeCollection.appendChild(html);
	}

	// renders the pull page pipe element
	poda.renderPipeElementFull = function(element, focus_search_bar=false){
		let html = createElementFromHtml(poda.tmpl_element_full(element));
		poda.dom.element.appendChild(html);
		console.log(element)

		let optionsPanel = $('#poda-element-options');
		if (optionsPanel) {
			if (poda.options_collapsed) { optionsPanel.removeClass('show'); }
			else { optionsPanel.addClass('show'); }
		}

		if (focus_search_bar) { $('.poda-search').focus(); }
	}


	// prepares the selected element and returns its modified html
	poda.prepareSelected = function(element, html) {

		//console.log("selected: " + element.eId);
		$(html).addClass('poda-element-selected');
		$(html).find('.btn-facet').addClass('btn-success');

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
	poda.addRootElement =  function(event) {
		console.log("Add root element");
		pipeID = event.target.parentElement.parentElement.attributes["pipe-id"].value
		console.log(pipeID)
		poda.showLoadingIcon();
		fetch('/pipe/add/?pID=' + pipeID, {method:'PUT'})
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
		pipeID = event.target.parentElement.parentElement.attributes["pipe-id"].value
		poda.showLoadingIcon();
		fetch('/pipe/selected/?pID=' + pipeID, {method:'DELETE'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id, true); poda.hideLoadingIcon(); })
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	// if user clicks on the "/", notifies server to replace facet with a root facet
	poda.switchToRoot = function() {
		console.log("switchToRoot");
		poda.showLoadingIcon();
		var el = poda.selected;
		poda.showLoadingIcon();
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
		let eId = poda.selected.eId;
		let query = domSearchBox.value;
		poda.showLoadingIcon();
		console.log(query)
		fetch('/search/?query='+query+'&eID='+eId)
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
	    let x = document.getElementsByClassName("poda-term-label");
		let el = poda.selected;

		if(event.target.classList.contains("intersecLabel"))
		{
			if(!poda.editMode)
			{
				termID = event.target.attributes["termid"].value
				poda.updatePipeElementPath.call(this, event, termID)
				return
			}
		}

		if (event.target.tagName == "MARK")
			poda.handleEntitityClick(event)
		else
		{
			if(poda.editMode)
			{
				poda.edit(event)
				return
			}
				
			if(event.target.attributes["class"].value == "poda-term-child-count" || event.target.attributes["class"].value == "entitySpan")
				var term = event.target.parentElement.dataset.tid
			else
				var term =	event.target.dataset.tid
			poda.setSelected(term, el.eId)
			//else
			//poda.updatePipeElementPath.call(this, event, term)
		}
	}

	function getSpan() {
		var selection = window.getSelection();
		var start = selection.anchorOffset;
		var end = selection.focusOffset;
		var anchorNode = selection.anchorNode;
		var focusNode = selection.focusNode;
		
		var startIndex = calculateOffset(anchorNode, start);
		var endIndex = calculateOffset(focusNode, end);

		if (startIndex > endIndex)
			return [endIndex, startIndex]
		else
			return [startIndex, endIndex]
	  }
	  
	  function calculateOffset(child, relativeOffset) {
		var parent = child.parentElement;
		var children = [];
	  
		displayOffset = parseInt(parent.parentElement.attributes["startChar"].value)
		// add the child's preceding siblings to an array
		for (var c of parent.childNodes) {
		  if (c === child) break;
		  children.push(c);
		}

		console.log(children.reduce((a, c) => a + c.textContent.length, 0))

		// calculate the total text length of all the preceding siblings and increment with the relative offset
		return displayOffset + relativeOffset + children.reduce((a, c) => a + c.textContent.length, 0);
	  }
	  

	poda.edit = function(event)
	{
		poda.selectedSpan = event.target;
		poda.selectedRange = getSpan();
		console.log(poda.selectedRange[0], poda.selectedRange[1])
	}

	poda.handleEntitityClick = function(event) {
		clickEvent = event
		
		console.log(clickEvent.target)

		var templateScript = Handlebars.compile(document.getElementById("poda-modal-tmpl").innerHTML);
		spanID = clickEvent.target.attributes.spanid.value;
		parentID = clickEvent.target.attributes.parentID.value;
		var isTrue = (clickEvent.target.attributes["deleted"].value === 'True');
		var context = { "name" : clickEvent.target.innerText, "spanID" : spanID, "facet" : clickEvent.target.dataset.entity, "deleted" : isTrue};
		var html = templateScript(context);

		//document.getElementById("myModal").innerHTML = html

		var modal = document.getElementById("myModal");
		modal.innerHTML = html

		modal.style.display = "block";
		var span = document.getElementsByClassName("close")[0];
		poda.selectedSpan = event.target

		if(document.getElementById("deleteEntity"))
		{
			document.getElementById("deleteEntity").onclick = function()
			{
				console.log(spanID);
				poda.showLoadingIcon()
				fetch('/hideEntity?spanID='+spanID, {method:'PUT'})
				.then(response => response.json())
				.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
				.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
				modal.style.display = "none";
				//poda.refreshElement();
			}
		}

		if(document.getElementById("restoreEntity"))
		{
			document.getElementById("restoreEntity").onclick = function()
			{
				console.log(spanID);
				poda.showLoadingIcon()
				fetch('/restoreEntity?spanID='+spanID, {method:'PUT'})
				.then(response => response.json())
				.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
				.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
				modal.style.display = "none";
				//poda.refreshElement();
			}
		}
		
		document.getElementById("goToPath").onclick = function(event)
		{
			console.log(event)
			console.log(spanID);
			poda.updatePipeElementPath.call(this, event, parentID, false);
			modal.style.display = "none";
			//poda.refreshElement();
		}


		span.onclick = function() {
			modal.style.display = "none";
		}

		window.onclick = function(event) {
			if (event.target == modal) {
				modal.style.display = "none";
				console.log(clickEvent)
			}
		} 

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
		console.log("termSelection: " + operation + "(eId=" + eId + ")");
		if(operation == "ALL")
		{
			console.log(poda.selected)
			for (x = 0; x < document.getElementsByTagName('input').length; x++) 
			{
				if (document.getElementsByTagName('input').item(x).type == 'checkbox') 
				{
					document.getElementsByTagName('input').item(x).checked = true;
				}
			}
		}

		if(operation == "CLEAR")
		{
			console.log(poda.selected)
			for (x = 0; x < document.getElementsByTagName('input').length; x++) 
			{
				if (document.getElementsByTagName('input').item(x).type == 'checkbox') 
				{
					document.getElementsByTagName('input').item(x).checked = false;
				}
			}
		}

		if(operation == "INVERT")
		{
			console.log(poda.selected)
			for (x = 0; x < document.getElementsByTagName('input').length; x++) 
			{
				if (document.getElementsByTagName('input').item(x).type == 'checkbox') 
				{
					check = document.getElementsByTagName('input').item(x).checked; 
					check = !check;
					document.getElementsByTagName('input').item(x).checked = check;
				}
			}
		}

		//poda.showLoadingIcon();
		//fetch('/pipes/'+poda.pipeId+'/elements/'+eId+'/selection/'+operation, {method:'PUT'})
		//.then(response => response.json())
		//.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		//.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	// when user clicks inside "Facets" (the root element) on a term, add it as a new facet
	poda.updatePipeElementPath = function(event, term, isSpan = false) {

		console.log(isSpan, "is span?")
		if(event.target.type == "checkbox")
			return;

		if(event.target.id == "label") 
			term = event.target.parentElement.dataset.tid;

		if(event.target.classList.contains("intersecLabel"))
		{
			var el = poda.selected;
			poda.showLoadingIcon();
			fetch('/elements/' + el.eId + '/path/?tID='+term, {method:'PUT'})
			.then(response => response.json())
			.then(pipe => {
				poda.preparePipe(pipe);
				poda.renderPipe(pipe.history_id, true);
				poda.hideLoadingIcon();
			})
			.catch(reason => {console.log(reason.message); });
			event.preventDefault();
			return
		}
		
		if (event.currentTarget.className == "poda-term-label")
		{
			console.log("Here")

			var el = poda.selected;
			if(event.currentTarget.attributes["isSpan"].value == "true" || isSpan)
			{
				poda.showLoadingIcon();
				fetch('/elements/' + el.eId + '/path/span/?tID='+term, {method:'PUT'})
				
				.then(response => response.json())
				.then(pipe => {
					poda.preparePipe(pipe);
					poda.renderPipe(pipe.history_id, true);
					poda.hideLoadingIcon();
				})
				.catch(reason => {console.log(reason.message); });
				event.preventDefault();
			}
			else
			{
				poda.showLoadingIcon();
				var el = poda.selected;
				fetch('/elements/' + el.eId + '/path/?tID='+term, {method:'PUT'})
				.then(response => response.json())
				.then(pipe => {
					poda.preparePipe(pipe);
					poda.renderPipe(pipe.history_id, true);
					poda.hideLoadingIcon();
				})
				.catch(reason => {console.log(reason.message); });
				event.preventDefault();
				
			}
		}
		else
		{
			var el = poda.selected;
			if(!isSpan)
			{
				poda.showLoadingIcon();
				fetch('/elements/' + el.eId + '/path/?tID='+term, {method:'PUT'})
				.then(response => response.json())
				.then(pipe => {
					poda.preparePipe(pipe);
					poda.renderPipe(pipe.history_id, true);
					poda.hideLoadingIcon();
				})
				.catch(reason => {console.log(reason.message); });
				event.preventDefault();
			}
			else
			{
				poda.showLoadingIcon();
				fetch('/elements/' + el.eId + '/path/span/?tID='+term, {method:'PUT'})
				.then(response => response.json())
				.then(pipe => {
					poda.preparePipe(pipe);
					poda.renderPipe(pipe.history_id, true);
					poda.hideLoadingIcon();
				})
				.catch(reason => {console.log(reason.message); });
				event.preventDefault();
			}
			
		}
		
		console.log(poda.selected.path)


		return false;
	}

	// Refresh the display
	poda.refreshElement = function() {
		// var el = poda.getEnclosingPipeElement(this);
			var el = poda.selected;
			path = poda.selected.path
			if(path.length == 0)
			{
				isSpan = false
			}
			else
			{
				isSpan = path[path.length-1]["isSpan"]
			}
			
			if(!isSpan)
			{
				poda.showLoadingIcon();
				fetch('/elements/' + el.eId + '/path/?tID='+ el.tId, {method:'PUT'})
				//fetch('/pipes/'+poda.pipeId+'/elements/'+el.eId+'/path/', {method:'PUT',body:this.dataset.tid})
				.then(response => response.json())
				.then(pipe => {
					poda.preparePipe(pipe);
					poda.renderPipe(pipe.history_id, true);
				})
				.catch(reason => {console.log(reason.message);});
			}
			else
			{
				poda.showLoadingIcon();
				fetch('/elements/' + el.eId + '/path/span/?tID='+ el.tId, {method:'PUT'})
				//fetch('/pipes/'+poda.pipeId+'/elements/'+el.eId+'/path/', {method:'PUT',body:this.dataset.tid})
				.then(response => response.json())
				.then(pipe => {
					poda.preparePipe(pipe);
					poda.renderPipe(pipe.history_id, true);
				})
				.catch(reason => {console.log(reason.message);});
			}

			poda.spansToAdd = []
			poda.hideLoadingIcon();
			return false;
	}



	// shows the element content if clicked on a pipe element
	poda.selectPipeElement = async function(event){

		pID = event.currentTarget.parentNode.attributes["pipe-id"].value
		let eId = event.currentTarget.attributes["data-elementid"].value;
		if(event.target.id == "el-options")
		{			
			//fetch('/getRanking/?pID='+pID+'&eId=' + eId, {method:'PUT'})
			//	.then(response => response.json());
			event.stopImmediatePropagation()
			var templateScript = Handlebars.compile(document.getElementById("poda-modalOptions-tmpl").innerHTML);
			var selected = poda.pipeCollection["pipes"][pID]["elements"][eId].ranking
			var context = { "ranking" : selected};
			var html = templateScript(context);

			//document.getElementById("myModal").innerHTML = html

			var modal = document.getElementById("myModal");
			modal.innerHTML = html

			modal.style.display = "block";
			var span = document.getElementsByClassName("close")[0];

			$('#btnDelteYes').click(function () {
				var ranking = $('#rankingSelector')[0].checked
				modal.style.display = "none";
				poda.showLoadingIcon();
				fetch('/setRanking/?pID='+pID+'&eId=' + eId + "&ranking=" + ranking, {method:'PUT'})
				.then(response => response.json())
				.then(pipe => {
				poda.preparePipe(pipe);
				poda.renderPipe(pipe.history_id, true);
				poda.hideLoadingIcon();})
			});

			$('#btnDelteNo').click(function () {
				modal.style.display = "none";
			});
			
			span.onclick = function() {
				modal.style.display = "none";
			}
	
			window.onclick = function(event) {
				if (event.target == modal) {
					modal.style.display = "none";
				}
			} 

		return
		}
		
		if(event.target.id == "pipe-name")
		{
			event.stopImmediatePropagation()
			var queryName = prompt("Enter the desired name for the query.");
			if( queryName != null)
			{
				poda.showLoadingIcon();
				fetch('/updatePipeName/?pID=' + pID + "&name=" + queryName, {method:'PUT'})
				.then(response => response.json())
				.then(pipe => {
				poda.preparePipe(pipe);
				poda.renderPipe(pipe.history_id, true);
				poda.hideLoadingIcon();})
			}
			return
		}
		
		if(event.target.id == "dropdownMenuButton")
		{
			return
		}

		if(event.target.id == "dropdownOperator")
		{
			event.target.parentElement.previousElementSibling.innerText = event.target.text
			operator = event.target.attributes["operator"].value

			pID = event.currentTarget.parentNode.attributes["pipe-id"].value
			console.log("HERE", pID)
			poda.showLoadingIcon();
			fetch('/updateOperator/?pID='+pID+'&eId=' + eId + "&operator=" + operator, {method:'PUT'})
			.then(response => response.json())
			.then(pipe => {
			poda.preparePipe(pipe);
			poda.renderPipe(pipe.history_id, true);
			poda.hideLoadingIcon();
			})
			.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
			event.stopImmediatePropagation()
			return
		}

		event.stopImmediatePropagation()
		//if (poda.selected != null && eId == poda.selected.eId) { console.log("Already selected."); return; }
		console.log("Change selected element to: " + eId);

		poda.showLoadingIcon();
		fetch('/pipe/selected/?eId='+eId+'&pID='+pID, {method:'PUT'})
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
		console.log(element)
		poda.clearDOM(poda.dom.element);
		poda.renderPipeElementFull(element, focus_search_bar);
	}


	// loads more child terms for the selected element
	poda.loadMoreChildTerms = function(event) {
		console.log(event.target)
		console.log('Load more terms...');
		poda.showLoadingIcon();
		fetch('loadMore/')
		.then(response => response.json())
		.then(element => {
			poda.replaceSelectedElement(element);
			poda.hideLoadingIcon();
			//poda.setHistoryId(element.history_id); // do not store in history
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}

	// Set the clicked term as selected
	poda.setSelected = function(tID, eID) {

		poda.showLoadingIcon();
		fetch('setSelected/?termID=' + tID + "&elID=" + eID, {method: 'PUT'})
		.then(response => response.json())
		.then(pipe => {poda.preparePipe(pipe); poda.renderPipe(pipe.history_id); poda.hideLoadingIcon();})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
	}


	// change sorting mode of selected element if clicked on upscore, downscore or label
	poda.sortTermsBy = async function(sortBy) {

		console.log("sort terms by: " + sortBy);
		poda.showLoadingIcon();
		console.log(poda.pipe)
		await fetch('/sortby/?mode=' + sortBy, {method: 'PUT'})
		.then(response => response.json())
		.then(pipe => {
			console.log("pipe:", pipe);
			poda.preparePipe(pipe);
			poda.renderPipe(pipe.history_id, true);
			poda.hideLoadingIcon();
		})
		.catch(reason => {console.log(reason.message); poda.hideLoadingIcon();});
		//poda.refreshElement();
		//location.reload();
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
		let i1 =  evt.oldIndex ;
		let i2 =  evt.newIndex ;

		// use endpoint according to drag & drop type
		let t = poda.dragndrop.type;
		let typeName = t.charAt(0).toUpperCase() + t.slice(1); // capitalize
		console.log(t + ': ' + i1 + ' => ' + i2);
		fetch('/drag/?index1=' + i1 + "&index2=" + i2, { method: 'PUT' })
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
	console.log("poda:", poda)

});


function createElementFromHtml(html) {

	var result = document.createElement('div');
	result.innerHTML = html.trim();
	return result.firstElementChild;
}
